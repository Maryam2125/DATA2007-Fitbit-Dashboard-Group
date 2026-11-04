# Software Requirements
 
## Requirements
 
| ID | Category | Requirement | Owner(s) | Priority | Done? | Notes | Feasibility |
|---|---|---|---|---|---|---|---|
| R01 | Goals and tracking | The dashboard shall let users set personal goals for steps, calories burned, active minutes and sleep. | Maryam | Must | Yes | Daily goals | OK |
| R02 | Goals and tracking | The dashboard shall show actual vs target for each goal for each day in the selected date range, with a 'met' or 'not met' indicator. | Maryam | Must | Yes | Daily goals | OK |
| R03 | Goals and tracking | The dashboard shall show a monthly calendar where each day is colour-coded by how many goals were met. | Sam | Should |  | Monthly wellness calendar | OK |
| R04 | Goals and tracking | The dashboard shall show each user's current streak of consecutive days a goal was met, defaulting to 10,000 steps. | Sam | Should |  | Monthly wellness calendar | OK |
| R05 | Friends, leaderboard and privacy | The dashboard shall treat other user IDs as 'friends' and only show another user's data where permission is granted (simulated). | Zoe | Must | Yes | Friends | OK |
| R06 | Friends, leaderboard and privacy | The dashboard shall rank the user against their friends on a chosen metric, with daily, weekly and monthly views. | Zoe | Must |  | Friends | Reworded |
| R07 | Friends, leaderboard and privacy | The dashboard shall show whether each user is in the top or bottom half of the group for average daily steps. | Zoe | Should | No | Friends | OK |
| R08 | Friends, leaderboard and privacy | The dashboard shall not show weight or BMI on group views, including the leaderboard, only on the user's own page. | Zoe | Must | Yes | Friends (weight is sentisite and sparse data so we want to exclude anyway) | OK |
| R09 | Trends and activity | The dashboard shall show daily trends in step count over time. | Sam | Must |  | Monthly trend | OK |
| R10 | Trends and activity | The dashboard shall show daily trends in calories burned over time. | Sam | Must |  | Monthly trend | OK |
| R11 | Trends and activity | The dashboard shall show daily trends in sleep duration over time. | Sam | Should |  | Monthly trend | OK |
| R12 | Trends and activity | The dashboard shall show time spent at each activity level (sedentary, light, fairly active, very active) so periods can be compared. | Sophie | Must | Yes | Behaviour insights | OK |
| R13 | Trends and activity | The dashboard shall highlight significant increases or decreases in activity compared with the user's usual level. | Sophie | Could | Yes | Behaviour insights | OK |
| R14 | Trends and activity | The dashboard shall let users compare steps, calories and active minutes across periods to see whether they have improved or declined. | Sophie | Should | Yes | Behaviour insights | Reworded |
| R15 | Trends and activity | The dashboard shall show a simple weekday vs weekend activity comparison. | Sophie | Could | Yes | Behaviour insights | OK |
| R16 | Trends and activity | The dashboard shall show an estimated average walking speed from distance and active minutes. | Dan | Could |  | Rough estimate only. Label as 'approximate speed'. | Challenging |
| R17 | Trends and activity | The dashboard shall show a sleep score between 0 and 10. | Maryam | Should | Yes | Daily goals | Reworded |
| R18 | Layout and usability | The dashboard shall show key performance indicators at the top of the page. | Maryam | Must | Yes | Suggested KPIs: average steps, calories, active minutes, goals met. This could just be a message to say this month so far you have me X number of your daily goals? | OK |
| R19 | Layout and usability | The dashboard shall use chart types suited to trend analysis (e.g. line and bar charts). | All | Must |  | Design rule | OK |
| R20 | Data handling and performance | The dashboard shall show a 'No data' message instead of errors or misleading zeros when data is missing. | All | Must |  | Design rule | OK |
| R21 | Data handling and performance | The dashboard shall calculate daily figures per calendar day, weekly figures Monday to Sunday, and monthly figures per calendar month. | Sam | Must |  | Monthly wellness calendar | OK |
| R22 | Data handling and performance | The dashboard shall update all charts within 3 seconds when a filter is changed. | All | Should |  | Design rule | OK |
| R23 | Layout and usability | The dashboard shall provide a date range filter that applies to all charts e.g. ours will show April | Unassigned | Must | Yes | Lots of the requirements assume a date range or a specific date is being viewed at a time e.g the current date so we need to show this somehow | OK |
| R24 | Layout and uasability | Welcome page with user name & welcome back message? | Sophie | Should | Yes | Streamlit setup | OK |
| R25 | Goals and tracking | The dashboard shall provide default goals (10,000 steps, 150 active minutes per week) if the user has not set any. | Maryam | Should | Yes | Daily goals | OK |
| R26 | Data handling and performance | The system shall load the CSV files into one cleaned dataset (consistent user IDs and dates) before use. | Unassigned | Must | Yes | Everything depends on it; each file formats dates differently. | OK |
| R27 | Goals and tracking | The dashboard shall highlight the user's best and worst day for each metric in the selected period. | Sophie | Should | Yes | Behaviour insights | OK |
| R28 | VO2 max estimation | The dashboard shall provide an estimated VO2 max score where sufficient data is available. | Dan | Could |  | VO2 Max | Challenging |
| R29 | Heart rate monitoring | The dashboard shall analyse heart-rate data to identify unusual readings and show changes during activity. | Dan | Could |  | VO2 Max related | Challenging |
 
## Excluded
 
| ID | Category | Requirement | Notes | Feasibility |
|---|---|---|---|---|
| X0 | Age estimation | Where age estimation is enabled the system shall display an estimated age with the data used. | Could be time consuming creating the metric | Not achievable |
 
## Summary
 
| Measure | Count |
|---|---|
| Total requirements | 29 |
| Must | 14 |
| Should | 10 |
| Could | 5 |
| Reworded | 3 |
| Not achievable (dropped) | 1 |
 
| Owner | Requirements involved |
|---|---|
| Dan | 3 |
| Sam | 6 |
| Zoe | 4 |
| Maryam | 5 |
| Sophie | 6 |
 
Owner counts include shared requirements, so they add up to more than the total.
 
## Flags
 
| Original requirement | Owner | Original priority | Problem | Suggestion |
|---|---|---|---|---|
| VO2 max estimation | Dan | Should | No heart rate data, which any VO2 estimate needs. | Drop it. Optionally mention as future work in the final report. |
| Heart rate monitoring | Dan | Must | No heart rate file in the dataset. | Drop it and remove the Must so it doesn't count against the MVP. |
| Hourly heart-rate trends | Maryam | - | No heart rate file in the dataset. | Drop it. |
| Age estimation | Sam | - | No age or demographic data. | Drop it. |
| Walking speed | Dan | Should | Only daily distance and active minutes, not true speed. | Keep as Could (R17), labelled 'approximate speed'. |
| Sleep score 0 to 10 | Sam | - | Data has minutes asleep and time in bed, not a score. | Define a formula as a team (R18). |
| Millisecond day boundaries | Sam | - | Data isn't that precise. | Keep Monday to Sunday rule, drop the milliseconds (R24). |
| 'Athletes' | Maryam | - | No athlete label in the data. | Use 'users' (R06, R12). |
 