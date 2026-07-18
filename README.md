# LLM-FanOut-FanIn

### Reason for this project 
It demonstrates the Fan-out, do many things, fan-in, collect the results, pattern using LLMs and Python.

### Project Presentations
 ai-concurrency-infographic-v3.html                
 ai-concurrency-infographic-v3.pdf 

### Lessons-Learned
 List of thing learned while creating this project.

### Pull down the code from GitHub
```
The easist way is to use the git command line tool.  
See the green code button on any github project page. 

git clone https://github.com/steve100/LLM-FanOut-FanIn.git

```


### Use Case One - Use an LLM

Run claude code to create a daily briefing from a set of sources.  
    The sources are in the briefing.md file.  The output is in dailybrief.log


### Setup your virtual environment
```
cd to your directory and run the following commands

Activate your virtual environment
Linux:   source .venv/bin/activate
windows: \.venv\Scripts\activate
```
### Setup your script to run the LLM
```
Select the model you want to use.
Edit dodailybrief.bat  || or dodailybrief.sh
```
###  Run the script
```
 The script will run claude code in batch mode using briefing.md 
 It will create two html files and a log file.
Linux:   ./dodailybrief.sh
windows: dodailybrief.bat

```
### Files created from the script   
```
   briefing-2026-07-17.html
   dailybrief.html
   dailybrief.log

```


### Use Case Two - Use Python to Create a Daily Briefing.
This will be cheaper than using an LLM  and it will be more robust.


```
Setup your virtual environment
cd to your directory and run the following commands

activate your virtual environment
Linux:   source .venv/bin/activate
windows: \.venv\Scripts\activate

```
```
run the Python script to create a daily briefing
  do-python-briefsteve.bat 
  or 

Run:
    python3 briefsteve.py --no-calendar --output morning-brief.md

```

### Initial Setup of the Python Virtual Environment
```
python -m venv .venv

Choose your os

Linux/macOS
#source .venv/bin/activate

Windows PowerShell
 .venv\Scripts\Activate.ps1

Windows Command Prompt
 .venv\Scripts\activate.bat

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt


For Google Calendar, create an OAuth Desktop application in Google Cloud, enable the Calendar API, download the credentials as credentials.json, and run without --no-calendar. The first execution opens the OAuth authorization flow and stores a reusable token locally. This follows Google’s official command-line quickstart pattern.
```

### LMM-FanOut-FanIn files
```
LICENSE
Lessons-Learned.txt
README.md
ai-concurrency-infographic-v3.html
ai-concurrency-infographic-v3.pdf
briefing-2026-07-17.html
briefing-20260717-063000.html
briefing.md
briefingcopy.md
briefsteve.py
create-github-repo.bat
dailybrief-haiku-example.html
dailybrief-sonnet-example.html
dailybrief.log
do-activate.bat
do-python-briefsteve.bat
dodailybrief.bat
dodailybrief.sh
morning-brief.md
requirements.txt
dailybrief-haiku-example.html
dailybrief-sonnet-example.html

```
