"""ScheduleCronTool prompt — mirrors src/tools/ScheduleCronTool/prompt.ts"""
SCHEDULE_CRON_TOOL_NAME = "ScheduleCron"

DESCRIPTION = "Schedule recurring tasks using cron expressions"

SCHEDULE_CRON_PROMPT = """Use this tool to schedule recurring tasks. You can:
1. Create cron jobs with CronCreate
2. List existing cron jobs with CronList
3. Delete cron jobs with CronDelete

Cron expressions use the standard 5-field format: minute hour day month weekday
Example: '0 9 * * *' runs daily at 9:00 AM."""
