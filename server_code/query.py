import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

# This is a server module. It runs on the Anvil server,
# rather than in the user's browser.
#
# To allow anvil.server.call() to call functions here, we mark
# them with @anvil.server.callable.
# Here is an example - you can replace it with your own:
#
# @anvil.server.callable
# def say_hello(name):
#   print("Hello, " + name + "!")
#   return 42
#
query_leave = """
WITH leave_request AS (
    SELECT 
        date(date_leave) AS date_leave, 
        name, 
        reason
    FROM (
        SELECT *,
               generate_series(start_date, end_date, '1 day'::interval) AS date_leave
        FROM ca_vn_agent_leave cval
        WHERE start_date BETWEEN date_trunc('month', (current_date + INTERVAL '1 month')) 
                            AND date_trunc('month', (current_date + INTERVAL '1 month') + INTERVAL '1 month') - INTERVAL '1 day'
        ORDER BY start_date
    ) AS subquery1
),

leave_schedule AS (
    SELECT 
        date_leave, 
        name, 
        type AS reason
    FROM (
        SELECT 
            date AS date_leave, 
            agent AS name,
            agent_email AS email,
            status AS type,
            EXTRACT(DAY FROM date) AS day, 
            EXTRACT(MONTH FROM date) AS month,
            EXTRACT(YEAR FROM date) AS year,
            ROW_NUMBER() OVER (PARTITION BY date, agent, channel ORDER BY status) AS row_num
        FROM vn_ca_agent_schedule_edit AS schedule
        WHERE date BETWEEN ((date_trunc('MONTH', CURRENT_DATE) + INTERVAL '1 MONTH - 1 day')::DATE - INTERVAL '9 days') 
                        AND (date_trunc('MONTH', CURRENT_DATE) + INTERVAL '1 MONTH - 1 day')::DATE 
          AND status IN ('X', 'AL', 'RO')
    ) AS subquery2
    WHERE row_num = 1
)

SELECT 
    date_leave, 
    name,
    CASE 
        WHEN reason = 'X' THEN 'Request Off' 
        --WHEN reason = 'DO' THEN 'Request Off' 
        WHEN reason = 'AL' THEN 'Annual Leave' 
        ELSE reason 
    END AS reason
FROM (
    SELECT *
    FROM leave_schedule

    UNION ALL

    SELECT *
    FROM leave_request
) AS combined_results;
"""