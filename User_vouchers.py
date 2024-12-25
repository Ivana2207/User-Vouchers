from flask import Flask, request, render_template, g, jsonify, Response
import sqlite3
import os
import requests
import json

# Database
DATABASE = os.getenv("DATABASE_PATH", "users_vouchers.db")

# Flask application
app = Flask(__name__)

# Database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

# Close the database connection after each request
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route("/")
def pocetna_strana():
    return '''
    <body style="background-color: #CCCCFF; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
        <h1 style="color: black;font-size: 50px;">Welcome!</h1>
    </body>
    '''


# Calculate total spending for a user
def get_total_spent(user_id):
    try:
        db = get_db()
        cursor = db.cursor()
        query = '''
            SELECT SUM(money_spent) AS total FROM user_spending WHERE user_id = ?
        '''
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        total_spent = row['total'] if row['total'] is not None else 0
        return total_spent
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

# Endpoint for total spending
@app.route('/total_spent/<int:user_id>', methods=['GET'])
def total_spent(user_id):
    total = get_total_spent(user_id)
    if total is not None:
        response = f"""
        <html>
        <head>
            <title>User Spending</title>
            <style>
                body {{
                    display: flex;
                    flex-direction: column;
                    justify-content: left;
                    align-items: left;
                    height: 100vh;
                    margin: 10;
                    background-color: #f5f5f5;
                }}
                h2 {{
                    margin-bottom: 20px;
                }}
                table {{
                    width: 30%;
                    border-collapse: collapse;
                    text-align: center;
                }}
                th, td {{
                    border: 2px solid black;
                    padding: 8px;
                }}
                th {{
                    background-color: #CCCCFF;
                }}
            </style>
        </head>
        <body>
            <h2>Spending Summary for User ID: {user_id}</h2>
            <table>
                <tr>
                    <th>User ID</th>
                    <th>Total Money Spent</th>
                </tr>
                <tr>
                    <td>{user_id}</td>
                    <td>{total}</td>
                </tr>
            </table>
        </body>
        </html>
        """
        return response
    else:
        return "<h2>No data available for this user</h2>", 404


# Calculate average spending by age groups
def get_average_spending_by_age():
    try:
        db = get_db()
        cursor = db.cursor()
        query = """
            SELECT 
                CASE 
                    WHEN user_info.age BETWEEN 18 AND 24 THEN '18-24'
                    WHEN user_info.age BETWEEN 25 AND 30 THEN '25-30'
                    WHEN user_info.age BETWEEN 31 AND 36 THEN '31-36'
                    WHEN user_info.age BETWEEN 37 AND 47 THEN '37-47'
                    ELSE '>47' 
                END AS age_group,
                AVG(user_spending.money_spent) AS average_spending
            FROM user_spending
            JOIN user_info ON user_spending.user_id = user_info.user_id
            GROUP BY age_group
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        result = {row['age_group']: row['average_spending'] for row in rows}
        return result
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

# Average spending by age
@app.route('/average_spending_by_age', methods=['GET'])
def average_spending_by_age():
    result = get_average_spending_by_age()
    if result is not None:
        rows = "".join(
            f"<tr><td>{age_group}</td><td>{average_spending:.2f}</td></tr>"
            for age_group, average_spending in result.items()
        )
        response = f"""
        <html>
        <head>
            <title>User Spending by Age Group</title>
            <style>
                table {{
                    display: flex;
                    flex-direction: column;
                    justify-content: left;
                    align-items: left;
                    height: 80vh;
                    margin: 10;
                    background-color: #f5f5f5;
                }}
                th, td {{
                    border: 2px solid black;
                    padding: 8px;
                }}
                th {{
                    background-color: #CCCCFF;
                }}
            </style>
        </head>
        <body>
            <h2>Average Spending by Age Group</h2>
            <table>
                <tr>
                    <th>Age Group</th>
                    <th>Average Spending</th>
                </tr>
                {rows}
            </table>
        </body>
        </html>
        """
        return response
    else:
        return "<h2>Unable to retrieve data</h2>", 500

#Write high spending user
@app.route('/write_high_spending_user', methods=['POST'])
def write_high_spending_user():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        if 'user_id' not in data or 'total_spending' not in data:
            return jsonify({"error": "Missing user_id or total_spending"}), 400

        user_id = int(data['user_id'])
        total_spending = int(data['total_spending'])

        db = get_db()


        cursor = db.cursor()
        cursor.execute("SELECT * FROM high_spenders WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()

        if existing_user:

            cursor.execute("UPDATE high_spenders SET total_spending = ? WHERE user_id = ?", (total_spending, user_id))
        else:

            cursor.execute("INSERT INTO high_spenders (user_id, total_spending) VALUES (?, ?)", (user_id, total_spending))

        db.commit()

        return jsonify({"message": "Data added or updated successfully."}), 201

    except sqlite3.Error as e:
        return jsonify({"error": "Database insertion/update error", "details": str(e)}), 500

    except Exception as ex:
        return jsonify({"error": "Unexpected error", "details": str(ex)}), 500



#Run the app
if __name__ == '__main__':
    app.run(debug=True)
