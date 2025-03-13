# Chrome Setup for Web Automation

Before running the LinkedIn scraper with Chrome, you need to ensure Chrome is properly set up:

## Install Chrome Browser

If you don't already have Chrome installed:
1. Download from [https://www.google.com/chrome/](https://www.google.com/chrome/)
2. Follow the installation instructions for your platform

## ChromeDriver Installation

The script uses the `webdriver-manager` package to automatically download and manage the ChromeDriver binary. This means you don't need to manually download ChromeDriver!

## Chrome Settings for Better Scraping

1. Open Chrome
2. Go to Chrome menu (three dots) > Settings
3. Go to "Privacy and security" section
4. Make sure LinkedIn.com is allowed to show pop-ups and use cookies
5. For improved reliability, you might want to log in to LinkedIn manually in Chrome before running the scraper

## Troubleshooting

If you encounter issues:

1. Ensure Chrome is up to date
2. Try clearing your Chrome browser cache
3. If you get a permission dialog, make sure to click "Allow"
4. Check that no other Chrome automation processes are running

## Environment Setup

The script will install the appropriate ChromeDriver version automatically via webdriver-manager.

After completing your scraping task, you may want to clear your browsing data for better security.