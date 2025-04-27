# Map-Scrapper
# Google Maps Lead Scraper GUI
A user-friendly desktop application built with Python (Tkinter and Selenium) to scrape business lead information from Google Maps searches or direct URLs.

## Features

*   **Easy-to-Use Interface:** Simple GUI built with Tkinter and modern ttk themes.
*   **Flexible Search:**
    *   Scrape based on **Business Type** and **Location** keywords.
    *   Scrape directly from a **Google Maps Search Results URL**.
*   **Data Extraction:** Extracts key business information:
    *   Business Name
    *   Address
    *   Phone Number
    *   Website URL
    *   Average Rating
    *   Number of Reviews
    *   Business Categories
*   **Configurable Scraping:**
    *   Set the desired **Number of Results** to scrape.
    *   Option to run Chrome in **Headless Mode** (no visible browser window).
    *   Adjustable **Delay** between actions to prevent blocking.
*   **Background Processing:** Scraping runs in a separate thread, keeping the UI responsive.
*   **Real-time Feedback:**
    *   Status updates displayed in the application log.
    *   Progress bar indicating scraping progress.
*   **Results Management:**
    *   View scraped data in a sortable, filterable table.
    *   **Export** results to CSV or Excel (`.xlsx`).
    *   Copy individual rows.
    *   Open business websites directly from the results table.
    *   Remove unwanted entries.
*   **Settings:**
    *   Specify custom paths for Chrome Browser and ChromeDriver.
    *   Configure **Proxy** settings (with optional authentication).
*   **Theming:** Basic Light/Dark mode toggle.
*   **Cross-Platform:** Designed to work on Windows, macOS, and Linux (requires appropriate Chrome/ChromeDriver).

## How It Works

The application uses the `selenium` library to automate the Google Chrome browser. It navigates to Google Maps, performs the specified search (or loads the provided URL), scrolls through the results list to load the desired number of businesses, and then clicks on each business listing to extract its details from the information panel. The process runs in a background thread (`threading`) to avoid freezing the Tkinter GUI, and updates are sent back to the main thread via a `queue`.

## Installation

1.  **Prerequisites:**
    *   **Python 3.7+:** Make sure you have Python installed. You can download it from [python.org](https://www.python.org/).
    *   **Google Chrome:** The script requires Google Chrome browser to be installed.
    *   **ChromeDriver:** You need the ChromeDriver executable that **matches your installed Google Chrome version**.
        *   Check your Chrome version (Help -> About Google Chrome).
        *   Download the corresponding ChromeDriver from the [official ChromeDriver website](https://chromedriver.chromium.org/downloads) or the [Chrome for Testing availability dashboard](https://googlechromelabs.github.io/chrome-for-testing/).
        *   **Important:** Place the downloaded `chromedriver` (or `chromedriver.exe` on Windows) executable either:
            *   In the same directory as the Python script (`scraper_app.py`).
            *   In a location included in your system's PATH environment variable.
            *   Or, specify its exact path in the application's **Settings** tab after launching.

2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/google-maps-scraper-gui.git
    cd google-maps-scraper-gui
    ```
    *(Replace `your-username/google-maps-scraper-gui` with your actual repository URL)*

3.  **Install Dependencies:**
    Create a `requirements.txt` file with the following content:
    ```txt
    selenium>=4.0.0
    pandas>=1.0.0
    openpyxl>=3.0.0
    # Add any other specific dependencies if needed
    ```
    Then install them:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the Application:**
    ```bash
    python scraper_app.py
    ```
    *(Make sure `scraper_app.py` is the name of your main Python file)*

2.  **Configure Search (Search Tab):**
    *   Choose **Search Method**:
        *   `Search by Keywords`: Enter the `Business Type` (e.g., "restaurants", "plumbers") and `Location` (e.g., "New York", "London EC1").
        *   `Use Direct URL`: Paste a valid Google Maps search results URL (e.g., `https://www.google.com/maps/search/cafes+in+san+francisco/...`).
    *   Set the `Number of Results` you want to scrape.
    *   Choose whether to run in `Headless Mode`.
    *   Adjust the `Delay` (in seconds) between actions if needed (higher values are safer but slower).
    *   Specify the `Output File` name (default: `google_maps_leads.csv`).

3.  **Start Scraping:**
    *   Click the `Start Scraping` button.
    *   Monitor the progress in the `Status` log and the progress bar.

4.  **Stop Scraping (Optional):**
    *   Click the `Stop` button at any time to interrupt the process gracefully.

5.  **View Results (Results Tab):**
    *   Once scraping is complete (or stopped), the results will be loaded into the table.
    *   Use the `Filter` box to search within the results.
    *   Click column headers to sort.
    *   Right-click on a row for options: `Copy`, `Open Website`, `Remove`.
    *   Use `Refresh` (if needed, though results load automatically) and `Export` to save the current view to CSV or Excel.

6.  **Adjust Settings (Settings Tab):**
    *   If Chrome or ChromeDriver are not found automatically, browse to their executable paths here.
    *   Configure proxy settings if required.
    *   Click `Save Settings` (Note: currently, this is a placeholder and doesn't persist settings between sessions unless you implement saving logic).

7.  **About Tab:**
    *   Basic information about the application.

## Configuration Options

*   **Chrome Path:** (Settings Tab) Manually specify the path to your `chrome.exe` (Windows) or `Google Chrome` (macOS/Linux) executable if the automatic detection fails.
*   **ChromeDriver Path:** (Settings Tab) Manually specify the path to your `chromedriver` executable if it's not in the script's directory or system PATH.
*   **Proxy Settings:** (Settings Tab) Configure HTTP/HTTPS proxies, including optional username/password authentication.

## Disclaimer

*   Web scraping can be resource-intensive for the target website. Use this tool responsibly.
*   Google Maps' website structure can change, which may break this scraper. Updates might be required to keep it functional.
*   Scraping Google Maps might be against their Terms of Service. Ensure you comply with their policies. The developers of this tool are not responsible for any misuse. Use at your own risk.
