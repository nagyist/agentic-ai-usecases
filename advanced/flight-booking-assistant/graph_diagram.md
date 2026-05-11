# Flight Booking Assistant Graph

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	router(router)
	info_extractor(info_extractor)
	city_lookup(city_lookup)
	conversation_driver(conversation_driver)
	confirm(confirm)
	search(search)
	select(select)
	payment(payment)
	pnr_lookup(pnr_lookup)
	done(done)
	__end__([<p>__end__</p>]):::last
	__start__ -.-> confirm;
	__start__ -.-> done;
	__start__ -.-> info_extractor;
	__start__ -.-> payment;
	__start__ -.-> router;
	__start__ -.-> select;
	city_lookup -.-> conversation_driver;
	confirm -.-> __end__;
	confirm -.-> search;
	conversation_driver -.-> __end__;
	done -.-> __end__;
	info_extractor -.-> city_lookup;
	info_extractor -.-> conversation_driver;
	info_extractor -.-> pnr_lookup;
	payment -.-> __end__;
	pnr_lookup -.-> __end__;
	router -.-> __end__;
	router -.-> conversation_driver;
	router -.-> info_extractor;
	search -.-> __end__;
	select -.-> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```
