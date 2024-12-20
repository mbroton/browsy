<div align="center">
  <h1>:performing_arts: browser-task</h1>
</div>

**browser-task** is a simple starter kit for executing browser automation tasks via HTTP requests. It uses Playwright for browser interactions and a lightweight SQLite-based queue for task management, making it easy to get started without requiring external databases or message brokers.

## Why browser-task?

* **🛠 Self-Contained:** No need for PostgreSQL, Kafka, or RabbitMQ—just run it locally or in a container.

* **🌐 Browser Automation Ready:** Execute tasks like web scraping, form submissions, and testing workflows with Playwright.

* **📋 Persistent Queue:** SQLite ensures tasks persist even if the server or workers restart.


## How It Works

* **Submit a Task:** Send an HTTP request to queue a browser automation task.

* **Workers Process Tasks:** Workers fetch tasks from the SQLite queue and execute them using Playwright.

* **Result Handling:** Customize worker logic to process results as needed (e.g., save screenshots, scrape data, or trigger other workflows).


## Limitations

* **🐢 Not Optimized for High Throughput:** The SQLite queue may introduce performance bottlenecks under heavy workloads due to database locking during task retrieval.

* **💼 Designed for Simplicity:** Ideal for small-scale or personal projects but not intended for large, distributed systems.


## Use Cases

* **Screenshot generation:** send a URL or raw HTML to the service and get a screenshot of the rendered page **(included in the template)**.

* **PDF Rendering:** submit a URL or HTML payload to generate and download a PDF of the page **(included in the template)**.

* **Basic Web Scraping:** extract data from a webpage, such as text or metadata.

* **Static HTML Previews:** convert raw HTML input into rendered page previews for QA or content review.


## Getting Started

* (Fork &) Clone the repository

* Set up and run the server and workers.

* Use the provided HTTP API to queue tasks and watch the workers execute them.
