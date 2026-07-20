set -euo pipefail

#Claude agent to fetch data and send to my website

#this assumes a directory - change as necessary
cd /home/test/project 

#sonnet
#/home/test/.local/bin/claude --model sonnet  -p "run briefing.md" --tools "Read,Write,WebFetch,WebSearch" --allowedTools "Read,Write,WebFetch,WebSearch"  > dailybrief.log 2>&1

#haiku
/home/test/.local/bin/claude --model haiku  -p "run briefing.md" --tools "Read,Write,WebFetch,WebSearch" --allowedTools "Read,Write,WebFetch,WebSearch"  > dailybrief.log 2>&1


