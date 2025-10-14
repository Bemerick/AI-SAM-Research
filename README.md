# SAM.gov API Client

A Python application for retrieving opportunities from SAM.gov using their public API.

## Overview

This application provides a simple interface to interact with the SAM.gov Get Opportunities Public API. It allows you to search for contract opportunities based on various parameters such as procurement type, notice ID, solicitation number, etc.

## Features

- Search for opportunities with various filter parameters
- Retrieve detailed information about specific opportunities
- RESTful API endpoints for integration with other applications

## Installation

1. Clone this repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your SAM.gov API key:

```
SAM_API_KEY=your_api_key_here
```

## Usage

1. Start the API server:

```bash
uvicorn app.main:app --reload
```

(base) bob.emerick@Mac AI-SAM % python app/analyze_opportunities.py --post-to-list --days 3

2. Access the API documentation at http://localhost:8000/docs

## API Reference

The application provides the following endpoints:

- `GET /opportunities/search`: Search for opportunities with various filter parameters
- `GET /opportunities/{notice_id}`: Get details for a specific opportunity by notice ID

For detailed API documentation, refer to the Swagger UI at http://localhost:8000/docs when the server is running.

## How to Get a SAM.gov API Key

To use this application, you need a SAM.gov API key:

1. Register on [SAM.gov](https://sam.gov)
2. Navigate to your Account Details page
3. Request a public API key
4. Use this key in your `.env` file

## License

MIT
