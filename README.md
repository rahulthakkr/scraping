# LinkedIn Profile Scraper

A Python script that automates searching for LinkedIn profiles based on specific keywords and extracts basic information from each profile.

## Features

- Automated login to LinkedIn
- Search for people using specific keywords (e.g., "founder")
- Visit each profile in the search results
- Extract basic profile information:
  - Name
  - Headline
  - Location
  - About section
  - Current position
  - Profile URL
- Save all data to a CSV file

## Requirements

- Python 3.6+
- Chrome browser installed (see chrome_setup_guide.md for setup instructions)
- LinkedIn account

## Installation

1. Clone this repository or download the script
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

1. Open the `linkedin_scraper.py` file and replace the placeholder credentials with your LinkedIn login information:

```python
# Replace with your LinkedIn credentials
EMAIL = "your_email@example.com"
PASSWORD = "your_password"
```

2. Customize the search term and number of pages to scrape:

```python
# Search term and number of pages to scrape
SEARCH_TERM = "founder"
NUM_PAGES = 3
```

3. Run the script:

```bash
python linkedin_scraper.py
```

The script will:
- Log in to LinkedIn using your credentials
- Search for people with the specified search term
- Visit each profile and extract information
- Save the data to a CSV file named `linkedin_profiles.csv`

## Customization

- To run the browser in headless mode (without UI), uncomment the following line in the `setup_driver` method:
  ```python
  # options.add_argument("--headless")
  ```

- To change the output file name, modify the `save_to_csv` call in the `run` method:
  ```python
  self.save_to_csv("custom_filename.csv")
  ```

- To extract additional profile information, modify the `scrape_profile` method.

## Important Notes

- LinkedIn may detect and block automated scraping. Use this script responsibly and at your own risk.
- Add random delays between actions to avoid detection.
- LinkedIn's HTML structure may change over time, requiring updates to the XPath selectors.
- This script is for educational purposes only. Always respect LinkedIn's Terms of Service.

## Troubleshooting

- If you encounter login issues, try increasing the sleep time after login.
- If profile data is not being extracted correctly, check and update the XPath selectors.
- If you get blocked by LinkedIn, try using a different IP address or wait before trying again. 