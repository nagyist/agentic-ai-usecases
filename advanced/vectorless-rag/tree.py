"""
tree.py
-------
Parses a PDF into a hierarchical DocumentTree using PyMuPDF4LLM.

Uses layout-aware PDF parsing without vector embeddings.
Strategy:
1. Extract markdown with layout preservation using PyMuPDF4LLM
2. Parse markdown headers into tree hierarchy
3. Use page_chunks for accurate page boundary detection

Install: pip install PyMuPDF pymupdf4llm
"""

import os
import re
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
import pymupdf4llm  # Primary parser


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class TreeNode:
    """Hierarchical document node"""
    id: str
    title: str
    level: int  # 0=root, 1=chapter, 2=section, 3=subsection
    page_start: int
    page_end: int
    content: str
    children: List['TreeNode'] = field(default_factory=list)
    heading_type: Optional[str] = None  # "numbered", "unnumbered", "page"
    summary: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level,
            "pages": f"{self.page_start}-{self.page_end}",
            "type": self.heading_type,
            "children_count": len(self.children),
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content
        }


@dataclass
class DocumentTree:
    """Complete document tree with metadata"""
    document_name: str
    root: TreeNode
    total_pages: int
    source_path: str = ""
    
    def print_tree(self, node: Optional[TreeNode] = None, indent: int = 0):
        """Pretty print tree structure"""
        if node is None:
            node = self.root
            print(f"\n📄 {self.document_name} ({self.total_pages} pages)")
        
        prefix = "  " * indent
        icon = "📑" if node.level == 0 else "📖" if node.level == 1 else "📄" if node.level == 2 else "📝"
        print(f"{prefix}{icon} [{node.level}] {node.title} (p{node.page_start}-{node.page_end})")
        
        for child in node.children:
            self.print_tree(child, indent + 1)




class PyMuPDF4LLMTreeBuilder:
    """
    Build hierarchical document trees using PyMuPDF4LLM.
    10x faster than GPU-based methods, no model download required.
    """
    
    def __init__(self, max_content_length: int = 8000):
        self.max_content_length = max_content_length
        
        # Heading detection patterns
        self.patterns = {
            'numbered_section': re.compile(r'^(?:\d+\.)+\s+(.+)$'),  # 1. Introduction, 2.3.1 Methods
            'roman_section': re.compile(r'^(?:[IVX]+)\.?\s+(.+)$', re.IGNORECASE),  # I. Introduction, II.3
            'letter_section': re.compile(r'^([A-Z])\.\s+(.+)$'),  # A. Methods, B. Results
            'unnumbered_heading': re.compile(r'^([A-Z][a-zA-Z\s]{3,50})$'),  # Abstract, Conclusion
        }
    
    def parse_pdf(self, pdf_path: str) -> DocumentTree:
        """
        Parse PDF into hierarchical tree structure.
        
        Strategy:
        1. Extract markdown with layout preservation using PyMuPDF4LLM
        2. Parse markdown headers into tree hierarchy
        3. Use page_chunks for accurate page boundary detection
        """
        pdf_path = Path(pdf_path)
        print(f"🔍 Parsing {pdf_path.name} with PyMuPDF4LLM...")
        
        start_time = time.time()
        
        # Method 1: Get full markdown for structure
        full_md = pymupdf4llm.to_markdown(str(pdf_path))
        
        # Method 2: Get page chunks for accurate pagination
        page_chunks = pymupdf4llm.to_markdown(
            str(pdf_path),
            page_chunks=True,
            write_images=False,
            embed_images=False
        )
        
        # Build page index for content lookup
        page_contents = {i+1: chunk["text"] for i, chunk in enumerate(page_chunks)}
        total_pages = len(page_chunks)
        
        # Parse structure from markdown
        root = self._build_tree_from_markdown(full_md, page_contents, pdf_path.name)
        
        elapsed = time.time() - start_time
        print(f"✅ Parsed in {elapsed:.2f}s: {total_pages} pages, {self._count_nodes(root)} nodes")
        
        return DocumentTree(
            document_name=pdf_path.stem,
            root=root,
            total_pages=total_pages,
            source_path=str(pdf_path)
        )
    
    def _build_tree_from_markdown(
        self, 
        markdown: str, 
        page_contents: Dict[int, str],
        doc_name: str
    ) -> TreeNode:
        """
        Parse markdown headers into hierarchical tree.
        Handles both numbered and unnumbered headings.
        """
        lines = markdown.split('\n')
        
        # Create root node
        root = TreeNode(
            id="root",
            title=doc_name,
            level=0,
            page_start=1,
            page_end=max(page_contents.keys()) if page_contents else 1,
            content="",
            heading_type="root"
        )
        
        # Stack maintains current path: (level, node)
        stack = [(0, root)]
        current_content_lines = []
        current_start_page = 1
        
        def flush_content():
            """Attach accumulated content to current node"""
            if current_content_lines and stack:
                content = '\n'.join(current_content_lines).strip()
                if content:
                    stack[-1][1].content += "\n\n" + content
                    # Generate summary from first paragraph
                    if not stack[-1][1].summary:
                        first_para = content.replace('#', '').strip()[:300]
                        stack[-1][1].summary = first_para
            current_content_lines.clear()
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Detect markdown headers
            if stripped.startswith('#'):
                flush_content()
                
                # Calculate level by counting # characters
                level = len(stripped.split()[0]) if stripped.split() else 0
                title = stripped.lstrip('#').strip()
                
                # Classify heading type
                heading_type = self._classify_heading(title)
                
                # Estimate page number based on content position
                # (We'll refine this using page_chunks later)
                page_num = self._estimate_page_number(i, len(lines), max(page_contents.keys()))
                
                # Create new node
                title_slug = '_'.join(re.findall(r'\w+', title))[:20]
                node_id = f"{title_slug}_{i}"
                new_node = TreeNode(
                    id=node_id,
                    title=title,
                    level=level,
                    page_start=page_num,
                    page_end=page_num,  # Will update later
                    content="",
                    heading_type=heading_type
                )
                
                # Attach to appropriate parent
                while stack and stack[-1][0] >= level:
                    closed_node = stack.pop()[1]
                    # Update parent's page_end
                    if stack:
                        stack[-1][1].page_end = max(stack[-1][1].page_end, closed_node.page_end)
                
                if stack:
                    parent = stack[-1][1]
                    parent.children.append(new_node)
                    parent.page_end = max(parent.page_end, page_num)
                
                stack.append((level, new_node))
                current_start_page = page_num
                
            else:
                current_content_lines.append(line)
            
            i += 1
        
        # Flush final content
        flush_content()
        
        # Refine page boundaries using page_chunks content matching
        self._refine_page_boundaries(root, page_contents)
        
        # Distribute content to leaf nodes
        self._distribute_content_to_leaves(root)
        
        return root
    
    def _classify_heading(self, title: str) -> str:
        """Classify heading as numbered, roman, letter, or unnumbered."""
        title = title.strip()
        
        if self.patterns['numbered_section'].match(title):
            return "numbered"
        elif self.patterns['roman_section'].match(title):
            return "roman"
        elif self.patterns['letter_section'].match(title):
            return "letter"
        elif self.patterns['unnumbered_heading'].match(title):
            return "unnumbered"
        else:
            return "unknown"
    
    def _estimate_page_number(self, line_idx: int, total_lines: int, total_pages: int) -> int:
        """Rough page estimation based on line position."""
        if total_pages == 0:
            return 1
        ratio = line_idx / total_lines if total_lines > 0 else 0
        return min(int(ratio * total_pages) + 1, total_pages)
    
    def _refine_page_boundaries(self, root: TreeNode, page_contents: Dict[int, str]):
        """
        Refine page boundaries by matching node content to page chunks.
        This corrects the rough estimates from markdown parsing.
        """
        def find_page_for_content(content: str, start_search: int = 1) -> int:
            """Find which page contains this content."""
            content_snippet = content[:100].strip()
            if not content_snippet:
                return start_search
            
            for page_num, page_text in page_contents.items():
                if page_num >= start_search and content_snippet in page_text:
                    return page_num
            return start_search
        
        def refine_node(node: TreeNode, parent_start: int = 1):
            # Update start page based on content match
            if node.content:
                matched_page = find_page_for_content(node.content, parent_start)
                node.page_start = matched_page
                node.page_end = matched_page
            
            # Process children
            prev_end = node.page_start
            for child in node.children:
                refine_node(child, prev_end)
                prev_end = max(prev_end, child.page_end)
            
            # Update node end to cover all children
            if node.children:
                node.page_end = max(c.page_end for c in node.children)
                node.page_start = min(c.page_start for c in node.children)
        
        refine_node(root)
    
    def _distribute_content_to_leaves(self, node: TreeNode):
        """
        Ensure content is stored at appropriate leaf nodes.
        If a node has children, its content becomes a summary.
        """
        if not node.children:
            return
        
        # Truncate content if node has children (it's a section header)
        if len(node.content) > 500:
            node.summary = node.content[:500] + "..."
            node.content = node.summary
        
        # Recurse
        for child in node.children:
            self._distribute_content_to_leaves(child)
    
    def _count_nodes(self, node: TreeNode) -> int:
        """Count total nodes in tree."""
        return 1 + sum(self._count_nodes(c) for c in node.children)


# Public API
def parse_pdf(pdf_path: str) -> DocumentTree:
    """Parse a PDF into a hierarchical document tree using PyMuPDF4LLM."""
    builder = PyMuPDF4LLMTreeBuilder()
    return builder.parse_pdf(pdf_path)
