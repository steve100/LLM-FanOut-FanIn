
Sections 2-6 below are independent research tasks (weather, lunar data, religious calendar, news). Gather them concurrently: issue all the needed searches/tool calls for these sections together in a batch rather than one at a time, then compose and print the sections in order once their data is ready. Use horizontal rules (---) to separate sections.

Do not fetch https://nineplanets.org (returns 403).


1. HEADER: Print "# Your daily morning brief for [Today's Date]"

2. WEATHER & OUTLOOK:
   - Summary: Condition and temp range for Chapel Hill, NC.
   - Times: Sunrise and Sunset.
   - Environment: Air Quality (AQI) and any active Advisories.
   - Activities: "Commute" and "Outdoor activity" recommendations based on weather.
   - Upcoming Week: A single compact line for the next 7 days: **Day**: Temp range, condition.

3. LUNAR STATUS:
   - Phase, Illumination %, and Moonrise/Moonset times for Chapel Hill, NC.

<!--
4. RELIGIOUS CALENDAR (Search-driven):
   - Check the Liturgical Year (Current Season).
   - Identify the Saint or Commemoration of the day (Check Episcopal 'Lesser Feasts & Fasts' or Roman Catholic 'General Roman Calendar').
   - Mention the Liturgical Color for the day.
   - List both and do not ask if I want to just have one
-->

<!--
5. CALENDAR:
   - Search primary Google Calendar for today. List events chronologically.
   - If empty, print "Your calendar is clear today."
-->

6. NEWS DIGEST (Search-driven):
   - AI News:  Top 5 headlines regarding AI
   - Global Security: Top 3 headlines regarding global war or unrest.
   - General News: Top 3 general global headlines (non-redundant).
   - Tech/DevOps: Top 5 updates (Target: CES 2026, SpaceX, AI Model releases).
   - Format: Bold bullet points with a 1-sentence summary each.
   - Source: List a good source after each headline
 

7. TECH RECOMMENDATIONS:
   - Provide one "Coding Tip of the Day" (Python, Bash, or DevOps automation).

STRICT RULE: Print the "Tech Recommendations" section last. Use '---' before every header except the first one.

find todays date-time 
use the Write tool to save the HTML output to both:
  - briefing-[date-time].html (timestamped version)
  - dailybrief.html (active copy)

<!--

8. SEND VIA FTP:
   - Run: ncftpput -f ncftp.conf . dailybrief.html
-->   
