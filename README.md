# LinkedIn Extractor

# Use Case
## Pull from LinkedIn your contacts and create a .csv file as a database
   - This does not violate any licencing.

# Initial Steps
## Access your LinkedIN profile's connections
   - list them
   - copy them to a word document.  a short example is small-list.docx

## Running it as a prompt in ChatGPT
   - "free" with your subscription or free plan
   - Make a new chat
   - paste the contents of Prompt-chatgpt.md into the window
   - upload the .docx file
   - push the run button

## Running it as a GPT
   - "free" with your subscription or free plan
   - Create a GPT
   - Put the contents of Prompt-chatgpt.md into the window
   - update it
   - publish it

## Running it as an API using a language like Python
   - About $0.30 for my list of 650 contacts using GPT-4o or GPT-5 (rounding)

## Running it as a python program
  -  "free"  You need a computer and you need to set it up.  See below
  -  Gives an answer faster than ChatGPT
  -  See run.bat
  -  uv run linkedin-extract %1 -o list-extracted.csv


**Extract LinkedIn contact data from `.docx` files and export to CSV.**

This tool parses Word documents exported from LinkedIn connection lists (e.g., via profile save or contact exports) and extracts structured data including name, description, connection date, LinkedIn URL, picture URL, and message link.

---

## 🚀 Features

- Reads `.docx` files directly (no manual formatting required)
- Extracts:
  - **Name** — hyperlinked LinkedIn contact name  
  - **Description** — text below the name (career summary, tagline, etc.)  
  - **Connected On** — normalized ISO date (`YYYY-MM-DD`)  
  - **LinkedIn URL** — main profile link  
  - **LinkedIn Picture URL** — generated automatically from profile link (`/overlay/photo/`)  
  - **Message URL** — hyperlink from the “Message” button  
- Exports clean CSV with columns:



---

## 🧩 Installation

### Option 1 — Run directly with [`uv`](https://github.com/astral-sh/uv)
```
#see run-linkedin-extract.bat
uv run linkedin-extract small-list.docx -o list-extracted.csv
```

### Option 2 — Manual setup
```
uv venv
source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
python extract_linkedin_docx.py small-list.docx -o list-extracted.csv
```

### 🧠 Example Output
```
Name	Description	Connected On	LinkedIn URL	LinkedIn Picture URL	Message URL
Mary Kay Wedel	Career Management Consultant | Helping Executives and Professionals accelerate career advancement, career change or career transition | LinkedIn Specialist | Resume Writer	2025-11-02	https://www.linkedin.com/in/marykaywedel
	https://www.linkedin.com/in/marykaywedel/overlay/photo/
	https://www.linkedin.com/messaging/thread/

A CSV file named list-extracted.csv will be created in the current directory.
```
### Adding Dependencies
```
If your script grows to include libraries like pandas or python-docx, add them via:
uv add pandas python-docx
```


"# LLM-FanOut-FanIn" 
