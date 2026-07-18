
rem claude agent to fetch data and send to my website

rem activate the Python virtual environment
echo "run this: .venv\Scripts\activate"

rem sonnet
rem
rem pick your home directory
rem cd /home/test/project 

rem del the log
delete  dailybrief.log

rem pick your model

rem sonnet 
rem echo Running Sonnet
rem assume claude code cli is on the path
rem claude --model sonnet -p "run briefing.md" --allowedTools "Read,Write,WebFetch,WebSearch" > dailbrief.log
rem claude --model sonnet -p "run briefing.md" --tools "Read,Write,WebFetch,WebSearch" --allowedTools "Read,Write,WebFetch,WebSearch" > dailybrief.log 2>&1


rem haiku
rem echo Running Haiku
rem assume claude code cli is on the path
claude --model haiku -p "run briefing.md" --tools "Read,Write,WebFetch,WebSearch" --allowedTools "Read,Write,WebFetch,WebSearch" > dailybrief.log 2>&1

rem  This will not copy to the web site
rem  Windows ftp tools are different than Linux tools
