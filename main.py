import psutil
import mysql.connector
import time
import pandas as pd
from db_details import CON_DATA

# CON_DATA = {
#     "host": "localhost",
#     "user": "",
#     "password": "",
#     "database": "mydb",
#     "collation": "utf8mb4_general_ci"
# }

cpu_frequency_desc = ['current', 'min', 'max']
cpu_loads_avg_desc = ['1_min', '5_min', '15_min']
memory_usage_desc = ['total', 'available', 'percent', 'used']
net_io_desc = ['Mbytes_sent', 'Mbytes_recv', 'packets_sent',
               'packets_recv', 'errin', 'errout', 'dropin', 'dropout']
temps_desc = ['current', 'high', 'critical']

LINE_AMOUNT = psutil.cpu_count(logical=True) + 1

mydb = mysql.connector.connect(**CON_DATA)


mycursor = mydb.cursor(buffered=True)

mycursor.execute(
    "CREATE OR REPLACE TABLE specs"
    "(id int auto_increment, cpu_percent varchar(10), "
    "cpu_frequency_desc varchar(10), cpu_frequency varchar(40), "
    "cpu_loads_avg_desc varchar(10), cpu_loads_avg varchar(40), "
    "memory_usage_desc varchar(10), memory_usage varchar(40), "
    "net_io_desc varchar(20), net_io varchar(40), "
    "temps_desc varchar(10), ssd_temps varchar(10), cpu_temps varchar(10), "
    "fan_label varchar(20), fan_speed varchar(20), "
    "primary key (id))")


psutil.cpu_percent()
init_list = [(None, )] * LINE_AMOUNT
mycursor.executemany(
    "INSERT INTO specs (cpu_percent) VALUES (%s)", init_list)


def mem_convert(value):
    if (type(value) is float):
        return round(value, 3)
    else:
        return value // 1024 // 1024
        # bytes // 1024 // 1024 = MB


def crit_check(crit, new):
    if crit is None or crit == "Normal" and new == "CRITICAL":
        return new
    return crit


def crit_high_check(a, b):
    try:
        if a <= b:
            return "Normal"
        else:
            return "CRITICAL"
    except TypeError:
        return None


def crit_low_check(a, b):
    try:
        if a >= b:
            return "Normal"
        else:
            return "CRITICAL"
    except TypeError:
        return None


def main():
    percents = []
    freqs = []
    loads = []
    mem = []
    net = []
    temps = []
    fans = []

    time.sleep(3)
    cpu_percent = psutil.cpu_percent(percpu=True)
    cpu_frequency = psutil.cpu_freq()
    cpu_loads_avg = psutil.getloadavg()
    memory_usage = psutil.virtual_memory()
    net_io = psutil.net_io_counters()
    sensors_temps = psutil.sensors_temperatures()
    sensors_fans = psutil.sensors_fans()

    crit = None
    for i, x in enumerate(cpu_percent):
        percents.append((x, i + 1))
        crit = crit_check(crit, crit_high_check(x, 90))
    percents.append((crit, LINE_AMOUNT))

    for i, x in enumerate(cpu_frequency):
        freqs.append(
            (cpu_frequency_desc[i], round(x, 3), i + 1))

    crit = None
    for i, x in enumerate(cpu_loads_avg):
        loads.append((cpu_loads_avg_desc[i],
                      round(x / psutil.cpu_count() * 100, 3), i + 1))
        crit = crit_check(crit, crit_high_check(x, 90))
    loads.append((None, crit, LINE_AMOUNT))

    for i, x in enumerate(memory_usage[:4]):
        if i == 3:
            x = memory_usage[0] - memory_usage[1]
        mem.append((memory_usage_desc[i], mem_convert(x), i + 1))
    mem.append((None, crit_high_check(mem[1][2], 90), LINE_AMOUNT))

    for i, x in enumerate(net_io):
        if i < 2:
            x = mem_convert(x)
        net.append((net_io_desc[i], x, i + 1))

    for i in range(2):
        temps.append((temps_desc[i], sensors_temps['nvme'][0][i + 1],
                      sensors_temps['k10temp'][0][i + 1], i + 1))
    temps.append((temps_desc[2], sensors_temps['nvme'][0][2],
                  90.0, 3))
    temps.append((None,
                  crit_high_check(temps[0][1], temps[2][1]),
                  crit_high_check(temps[0][2], temps[2][2]),
                  LINE_AMOUNT))

    crit = None
    for fan_list in sensors_fans.values():
        for id, fan in enumerate(fan_list):
            if fan.current == 0:
                speed = None
            else:
                speed = fan.current
            crit = crit_check(crit, crit_high_check(speed, 3000))
            crit = crit_check(crit, crit_low_check(speed, 100))
            fans.append((fan.label, fan.current, id + 1))
    fans.append((None, crit, LINE_AMOUNT))

    mycursor.executemany(
        "UPDATE specs SET cpu_percent=%s WHERE id=%s", percents)
    mycursor.executemany(
        "UPDATE specs SET cpu_frequency_desc=%s, cpu_frequency=%s "
        "WHERE id=%s", freqs)
    mycursor.executemany(
        "UPDATE specs SET cpu_loads_avg_desc=%s, cpu_loads_avg=%s "
        "WHERE id=%s", loads)
    mycursor.executemany(
        "UPDATE specs SET memory_usage_desc=%s, memory_usage=%s "
        "WHERE id=%s", mem)
    mycursor.executemany(
        "UPDATE specs SET net_io_desc=%s, net_io=%s "
        "WHERE id=%s", net)
    mycursor.executemany(
        "UPDATE specs SET temps_desc=%s, ssd_temps=%s, "
        "cpu_temps=%s WHERE id=%s", temps)
    mycursor.executemany(
        "UPDATE specs SET fan_label=%s, fan_speed=%s "
        "WHERE id=%s", fans)

    mycursor.execute("SELECT * FROM specs LIMIT 0")
    column_names = mycursor.column_names

    mycursor.execute("SELECT * FROM specs")
    full_info = []
    for i in mycursor:
        full_info.append(i)

    df = pd.DataFrame.from_records(
        full_info, index=[x[0] for x in full_info], columns=column_names)
    df = df.drop('id', axis=1)
    df['fan_label'] = df['fan_label'].replace('', None)
    print(df.fillna(value="-"), "\n")


if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("\nExiting...")
            break
    print("Exited successfully")
