from flask import Flask, request
import requests
from flask import jsonify
import re
import os
import argparse
import sqlite3
app = Flask(__name__)


"""Create cell function based on information passed in via curl"""


@app.route("/cells/<string:s>", methods=["PUT"])
def create_cells(s):
    try:
        # We assume that this spreadsheet doesn't use Excel formatting, and
        # uses the basic format of a single capital letter followed by a number.
        m = re.match("[A-Z]+(\d+)$", s)
        if bool(m) and m.group(1).isdigit() and 0 < int(m.group(1)) < 1000:
            try:
                js = request.get_json()
            except Exception as e:
                return "", 400
            id = js.get("id")
            formula = js.get("formula")
            expression = s
            if expression != None and id != None and formula != None:
                if expression == id:
                    if get_cell_from_source(s) is not None:
                        create_check = create_cell_in_source(id, formula, True)
                        if create_check is not None:
                            return "", 204
                        else:
                            return "", 500
                    else:
                        create_check = create_cell_in_source(
                            id, formula, False)
                        if create_check is not None:
                            return "", 201
                        else:
                            return "", 500

                else:
                    return "", 400
            else:
                return "", 400
        else:
            return "", 400
    except Exception as e:
        return f"An internal server error has occurred, with the exception {e}", 500


""" Function to calculate the value of a cell. If a cell's value doesn't eval(), it is 0,
Unless it is a divide by zero error, and then an error is thrown."""


def get_cell_value(s):
    try:
        cell = get_cell_from_source(s)
        if cell != None:
            list_of_var = re.findall("[A-Z]+\d+", cell)
            if len(list_of_var) == 0:
                val = eval(cell)
                return val
            else:
                for i in list_of_var:
                    retval = get_cell_value(i)
                    cell = cell.replace(str(i), str(retval))
                return eval(cell)
        else:
            return 0
    except ZeroDivisionError as e:
        # Case that the math evaluates incorrectly - e.g division by zero.
        # ONLY happens when eval() throws an exception. If the cell doesn't
        # exist, that's covered by returning 0
        return None
    except Exception as e:
        return 0


"""Gets cell value from specified database source, and passes it back
to the calculation functions"""


def get_cell_from_source(id):
    # Get cell based on if the -r flag is sqlite or firebase
    if db_type == "firebase":
        response = requests.get(url + "/cells/" + str(id)+".json")
        if response.status_code == 200 and response.json() is not None:
            return response.json()["formula"]
        else:
            return None
    elif db_type == "sqlite":
        try:
            with sqlite3.connect("sqldatabase.db") as connection:
                cursor = connection.cursor()
                cursor.execute(f"SELECT * FROM cells WHERE id = '{id}'")
            retval = cursor.fetchone()[1]
            connection.commit()
            connection.close()
            return retval
        except Exception as e:
            return None
    else:
        raise Exception("-r flag incorrectly set, options firebase or sqlite")


"""Deletes cell from specified database, either firebase or sqlite"""


def delete_cell_from_source(id):
    # Delete cell based on source
    if db_type == "firebase":
        response = requests.delete(url + "/cells/" + str(id) + ".json")
        if response.status_code == 200:
            return response
        else:
            return None
    elif db_type == "sqlite":
        try:
            with sqlite3.connect("sqldatabase.db") as connection:
                cursor = connection.cursor()
                cursor.execute(f"DELETE FROM cells WHERE id = '{id}'")
            connection.commit()
            connection.close()
            return cursor
        except:
            return None
    else:
        raise Exception("-r flag incorrectly set, options firebase or sqlite")


"""Creates or updates cell in the specified database structure,
Either with firebase or sqlite, depending on choice."""


def create_cell_in_source(id, formula, update_flag):
    if db_type == "firebase":
        response = requests.put(
            f"{url}/cells/{id}.json", json={'id': id, 'formula': formula})
        if response.status_code == 200 and response.json() is not None:
            return response.json()
        else:
            return None
    elif db_type == "sqlite":
        if update_flag == False:
            try:
                with sqlite3.connect("sqldatabase.db") as connection:
                    cursor = connection.cursor()
                    cursor.execute(
                        f"INSERT INTO cells(id,formula) VALUES ('{id}', '{formula}')")
                retval = cursor
                connection.commit()
                connection.close()
                return retval
            except Exception as e:
                return None
        else:
            try:
                with sqlite3.connect("sqldatabase.db") as connection:
                    cursor = connection.cursor()
                    cursor.execute(
                        f"UPDATE cells set formula = '{formula}' WHERE id = '{id}'")
                retval = cursor
                connection.commit()
                connection.close()
                return retval
            except Exception as e:
                return None
    else:
        raise Exception("-r flag incorrectly set, options firebase or sqlite")


""" Function to get all the cells from a specific database format,
either a requests call out to firebase, or connection to the sqlite db"""


def get_all_cells_from_source():
    if db_type == "firebase":
        response = requests.get(url + "/cells.json")
        if response.status_code == 200 and response.json() is not None:
            return response.json().keys()
        elif response.status_code != 200:
            return None
        else:
            # This is the case where the call succeeds, but the cells haven't been created
            return []
    elif db_type == "sqlite":
        try:
            with sqlite3.connect("sqldatabase.db") as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT id FROM cells")
            dbval = cursor.fetchall()
            connection.commit()
            connection.close()
            retval = [i[0] for i in dbval]
            return retval
        except Exception as e:
            return None
    else:
        raise Exception("-r flag incorrectly set, options firebase or sqlite")


"""Creates SQL db on start up - creates cells table. If the .db file is deleted mid-execution,
this function must be rerun"""


def create_sql_db():
    try:
        with sqlite3.connect("sqldatabase.db") as connection:
            cursor = connection.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS cells (id TEXT PRIMARY KEY NOT NULL, formula TEXT NOT NULL)")
        connection.commit()
        connection.close()
    except Exception as e:
        print(f"An error has occured configuring the database. See:\n{e}")


"""Function to get a specified cell's value"""


@app.route("/cells/<string:s>", methods=["GET"])
def get_cells(s):
    try:
        expression = s
        # We assume that this spreadsheet doesn't use Excel formatting, and
        # uses the basic format of a single capital letter followed by a number.
        # Range between [A-Z][1-999]
        m = re.match("[A-Z]+(\d+)$", expression)

        if bool(m) and m.group(1).isdigit() and 0 < int(m.group(1)) < 1000:
            exists_check = get_cell_from_source(expression)
            if exists_check is not None:
                try:
                    val = get_cell_value(expression)
                    if val != None:
                        ret_string = "\"id\":\"" + \
                            str(expression) + "\", \"formula\":\"" + \
                            str(val) + "\""
                        return ret_string, 200
                    else:
                        # This is the case for if a cell within a formula does not exist
                        return "", 404
                except Exception as e:
                    # This catches errors within the eval of the function get_cell_value
                    # Such as division by zero
                    return "", 404
            else:
                return "", 404
        else:
            return "", 404
    except Exception as e:
        return "", 500


"""Deletes a specified cell in the spreadsheet"""


@app.route("/cells/<string:s>", methods=["DELETE"])
def delete_cells(s):
    try:
        # We assume that this spreadsheet doesn't use Excel formatting, and
        # uses the basic format of a single capital letter followed by a number.
        m = re.match("[A-Z]+(\d+)$", s)
        if bool(m) and m.group(1).isdigit() and 0 < int(m.group(1)) < 1000:
            exists_check = get_cell_from_source(s)
            if exists_check is not None:
                deleted_check = delete_cell_from_source(s)
                # Delete occured, verify:
                if deleted_check is not None:
                    return "", 204
                else:
                    return "", 404
            else:
                return "", 404
        else:
            # This is just a shortcut - we know it has to follow the cell formatting.
            # This would probably be a 400, bad request, but delete can only return 404
            return "", 404
    except:
        return "", 500


"""Gets list of all cells in the spreadsheet"""


@app.route("/cells", methods=["GET"])
def get_list_of_cells():
    try:
        response = get_all_cells_from_source()
        if response is not None:
            return jsonify(list(response)), 200
        else:
            return "", 500
    except Exception as e:
        return "", 500


"""Handles any incorrect path calls."""


@app.errorhandler(404)
def wrong_route(error):
    return f"Error 404: The path {request.path} is not a valid option." + "\nOptions are:\nGET /cells\nGET /cells/id\nPUT /cells/id {\"id\":\"id\", \"formula\":\"formula\"}\nDELETE /cells/id\n", 404


"""Handles unallowed method error (e.g. trying to DELETE /cells)"""


@app.errorhandler(405)
def wrong_method(error):
    return f"The method you have tried to use at {request.path} is not allowed. Please verify the path-method combination is correct.", 404


"""Main function - checks args and runs app"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--db_type", help="Database type")
    args = parser.parse_args()
    db_type = args.db_type
    args_check = False
    if db_type == "firebase":
        args_check = True
        firebase_name = os.getenv("FBASE")
        if firebase_name is not None:
            url = "https://" + firebase_name + \
                "-default-rtdb.europe-west1.firebasedatabase.app"
        else:
            print("Firebase method selected, but no FBASE environment variable found.\nPlease check you have correctly exported your variable name.\nDefaulting to sqlite DB.")
            db_type = "sqlite"
    elif db_type == "sqlite":
        args_check = True
        try:
            create_sql_db()
        except Exception as e:
            print(
                f"Something has gone wrong creating the SQLite database. See error code: {e}")
    else:
        print("Database type variable incorrectly set. Format should be \"-r firebase\" or \"-r sqlite\"." +
              f"\nYou have inputted: {db_type}")
    if args_check is True:
        app.run(host="localhost", port=3000)
    else:
        print("The app will not start due to an error in your arguments.")
