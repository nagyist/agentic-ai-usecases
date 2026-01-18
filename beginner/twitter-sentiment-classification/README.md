# Twitter Sentiment Classification - Emotion Detection System

An end-to-end AI-powered system for classifying emotions in tweets using OpenAI's GPT-5-nano model.

## Overview

This project demonstrates how to build a production-ready emotion classification system that analyzes tweets and identifies emotional content across 5 distinct emotion categories: anger, disgust, happiness, surprise, and sadness.

### Key Features
- Multi-class emotion classification (5 emotions)
- Structured JSON output with emotion intensity scores
- Comprehensive evaluation metrics and cost analysis
- Token usage tracking for cost estimation
- Visualizations for performance analysis

---

## Dataset

### SMILE Twitter Emotion Dataset

**Source**: https://figshare.com/articles/dataset/smile_annotations_final_csv/3187909

**Citation**:
```
Wang, Bo; Tsakalidis, Adam; Liakata, Maria; Zubiaga, Arkaitz; Procter, Rob; Jensen, Eric (2016). 
SMILE Twitter Emotion dataset. figshare. Dataset. 
https://doi.org/10.6084/m9.figshare.3187909.v2
```

### Dataset Statistics

| Metric | Value |
|--------|-------|
| Total Tweets | 3,085 |
| Emotion Categories | 5 |
| Emotions | anger, disgust, happy, surprise, sad |
| Format | CSV with tweet_id, tweet_text, emotion |
| Evaluation Sample | 30 samples × 5 emotions = 150 tweets |

### Data Structure

The dataset is provided in CSV format with the following columns:
- **Column 1**: tweet_id (unique identifier)
- **Column 2**: tweet_text (the actual tweet content)
- **Column 3**: emotion (human-annotated emotion label)

---

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- OpenAI API key
- pip package manager

### Step 1: Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

### Required Packages

The `requirements.txt` file includes:
- `openai` - OpenAI API client
- `pandas` - Data manipulation and analysis
- `scikit-learn` - Machine learning metrics and utilities
- `matplotlib` - Data visualization
- `seaborn` - Statistical data visualization
- `google-genai` - (Optional) For alternative API integrations

### Step 2: Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
touch .env
```

Add your OpenAI API key to the `.env` file:

```
OPENAI_API_KEY=your-api-key-here
```

**Important**: Replace `your-api-key-here` with your actual OpenAI API key from https://platform.openai.com/api-keys

### Step 3: Verify Setup

Before running the full analysis, verify that your environment is correctly configured:

1. Ensure `.env` file exists in the project root
2. Verify `OPENAI_API_KEY` is set (check: `echo $OPENAI_API_KEY`)
3. Confirm all packages are installed: `pip list`
4. Check data file exists: `ls -la data/smile-annotations-final.csv`

---

## Project Structure

```
twitter-sentiment-classification/
├── README.md                                  # This file
├── requirements.txt                          # Python dependencies
├── .env                                      # Environment variables (create this)
├── twitter-sentiment-classification.ipynb    # Main analysis notebook
└── data/
    ├── smile-annotations-final.csv           # SMILE dataset (CSV format)
    └── smile-annotations-final.json          # SMILE dataset (JSON format)
```

---

## Usage

### Running the Analysis

Open and run the Jupyter notebook:

```bash
jupyter notebook twitter-sentiment-classification.ipynb
```

Execute cells sequentially to:
1. Load and explore the dataset
2. Initialize OpenAI API client
3. Define emotion classification prompts
4. Run classification on sample tweets
5. Evaluate performance
6. Analyze costs and token usage

### Workflow

The notebook follows this workflow:

1. **Data Loading** → Load SMILE dataset and explore emotion distribution
2. **API Setup** → Initialize OpenAI client with credentials
3. **Prompt Design** → Define structured prompts for emotion classification
4. **Classification** → Process 150 sample tweets (30 per emotion)
5. **Evaluation** → Calculate accuracy and per-class metrics
6. **Visualization** → Generate performance charts and confusion matrix
7. **Cost Analysis** → Track tokens and estimate costs for full dataset

---

## Input & Output

### Input

**Format**: Individual tweets (text strings)

**Example Input**:
```
"I absolutely love this beautiful day! Best moment ever!"
```

**Processing**: Each tweet is sent to the OpenAI API with a structured prompt requesting emotion intensity scores.

### Output

**Format**: JSON object with emotion intensity scores (0-1 scale)

**Example Output**:
```
{
  "anger": 0.0,
  "disgust": 0.0,
  "happy": 0.95,
  "surprise": 0.1,
  "sad": 0.0
}
```

**Interpretation**:
- Each emotion has an intensity score between 0 (not present) and 1 (extremely strong)
- The emotion with the highest score is selected as the predicted emotion
- Multiple emotions can have non-zero scores for mixed sentiments

### Output Data Structure

After processing all 126 tweets, results are stored in a pandas DataFrame with columns:

| Column | Description |
|--------|-------------|
| tweet_id | Original tweet identifier |
| tweet_text | The actual tweet content |
| emotion | Human-annotated true emotion |
| predicted_emotion | Model's predicted emotion |
| raw_prediction | Full JSON with all emotion scores |
| predicted_emotion_score | Confidence score of predicted emotion |
| input_tokens | Tokens used for input prompt |
| output_tokens | Tokens used for model output |

---

## Results & Metrics

### Evaluation Metrics

The analysis produces:

1. **Overall Accuracy**: Percentage of correctly classified tweets
2. **Per-Class Accuracy**: Accuracy broken down by emotion category
3. **Confusion Matrix**: Shows which emotions are confused with each other
4. **Token Statistics**: Input/output token counts for cost estimation

### Expected Performance

| Metric | Value |
|--------|-------|
| Overall Accuracy | ~77% |
| Happy Accuracy | ~100% (easiest to detect) |
| Anger Accuracy | ~90% |
| Sadness Accuracy | ~70% |
| Surprise Accuracy | ~60% |
| Disgust Accuracy | ~33% (hardest to detect) |

*Note: Actual results may vary based on prompt variations and model updates*

### Cost Information

**Pricing** (gpt-5-nano as of 2026):
- Input tokens: $0.05 per 1M tokens
- Output tokens: $0.40 per 1M tokens
- Cost for 126 samples: $0.0124
- Estimated cost for full dataset (1267 tweets): $0.12
- Estimated tokens: Input 268735, Output 276960

---

## Task Description

### Objective

Design an agentic AI system that:
1. Takes a tweet as input
2. Classifies the tweet into one of 5 emotion categories
3. Returns confidence scores for each emotion
4. Provides performance metrics and cost analysis

### Evaluation Approach

1. **Sample Selection**: Select 30 representative samples from each emotion category (~150 total)
2. **Classification**: Process each tweet through OpenAI API
3. **Accuracy Measurement**: Compare predicted emotions with human annotations
4. **Cost Estimation**: Track token usage and extrapolate to full dataset

### Deliverables

- ✅ Emotion classification for 150 test samples
- ✅ Accuracy metrics (overall and per-class)
- ✅ Performance visualizations (accuracy charts, confusion matrix)
- ✅ Token usage and cost analysis
- ✅ Cost extrapolation to full dataset

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| API Provider | OpenAI |
| Model | GPT-5-nano |
| Data Processing | pandas |
| ML Metrics | scikit-learn |
| Visualization | matplotlib, seaborn |
| Notebook Environment | Jupyter |

---


## For More Information

- **Full Tutorial**: See [Building an AI-Powered Tweet Emotion Classifier with OpenAI: A Complete Guide](https://medium.com/@alphaiterations/building-an-ai-powered-tweet-emotion-classifier-with-openai-a-complete-guide-8aa94d2c8174?postPublishedType=repub) for comprehensive step-by-step guide
- **OpenAI Documentation**: https://platform.openai.com/docs
- **SMILE Dataset**: https://figshare.com/articles/dataset/smile_annotations_final_csv/3187909
- **Jupyter Notebook**: [twitter-sentiment-classification.ipynb](twitter-sentiment-classification.ipynb)

---

## License & Attribution

Dataset sourced from Wang et al. (2016) - SMILE Twitter Emotion Dataset

This project is part of the Agentic AI Use Cases collection.