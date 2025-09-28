import pandas as pd
import mysql.connector

# 连接到MySQL数据库
conn = mysql.connector.connect(
    host="localhost",
    user="username",
    password="password",
    database="database_name"
)

# 查询数据
query = "SELECT * FROM aiueo"
data = pd.read_sql(query, conn)

# 导出为CSV文件
data.to_csv("output.csv", index=False)

# 关闭数据库连接
conn.close()