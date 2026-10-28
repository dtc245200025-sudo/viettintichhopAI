import os

import mysql.connector


ACCOUNT_QUERY = (
    "SELECT u.MaUser id,u.HoTen name,u.Email email,r.TenRole role,u.TrangThai active,u.NgayTao createdAt "
    "FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole ORDER BY u.MaUser"
)


def main() -> None:
    password = os.environ.get("VIETINCARE_LIST_APP_PASSWORD", "")
    if not password:
        print("APP_PASSWORD_REQUIRED")
        raise SystemExit(1)
    connection = None
    try:
        connection = mysql.connector.connect(
            host="127.0.0.1", port=3306, user="vietincare_app", password=password,
            database="qlkhviettin", connection_timeout=5, charset="utf8mb4",
            collation="utf8mb4_0900_ai_ci", time_zone="+00:00",
        )
        cursor = connection.cursor(dictionary=True, buffered=True)
        cursor.execute(ACCOUNT_QUERY)
        rows = cursor.fetchall()
        cursor.close()
    except mysql.connector.Error as error:
        print(f"MYSQL_ACCOUNT_CHECK_FAILED:{error.errno}")
        raise SystemExit(1) from None
    finally:
        if connection:
            connection.close()
    print(f"ACCOUNT_COUNT:{len(rows)}")
    print("ID\tSTATUS\tROLE\tNAME\tEMAIL\tCREATED_AT")
    for row in rows:
        status = "ACTIVE" if row["active"] else "LOCKED"
        print(f'{row["id"]}\t{status}\t{row["role"]}\t{row["name"]}\t{row["email"]}\t{row["createdAt"]}')


if __name__ == "__main__":
    main()
