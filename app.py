from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import re

app = Flask(__name__)
app.secret_key = 'tej_and_sush'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'tej@170104',
    'db': 'Recipe_Manager1',
}

def get_db_connection():
    return pymysql.connect(**db_config)

# Home Page - Display Categories
@app.route('/')
def home():
    user_info = {
        'is_authenticated': 'loggedin' in session,
        'username': session.get('username')
    }
    return render_template('home.html', user=user_info)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM User WHERE U_name = %s AND U_password = %s', (username, password))
                account = cursor.fetchone()
            if account:
                session['loggedin'] = True
                session['id'] = account[0]
                session['username'] = username
                return redirect(url_for('home'))
            else:
                msg = 'Incorrect username/password!'
        except Exception as e:
            msg = f"Error: {e}"
        finally:
            if connection:
                connection.close()
    return render_template('login.html', msg=msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
            return render_template('register.html', msg=msg)

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO User (U_name, U_password, email, U_role) VALUES (%s, %s, %s, "user")', 
                               (username, password, email))
                connection.commit()
            msg = 'You have successfully registered!'
        except Exception as e:
            msg = f"Error during registration: {str(e)}"
        finally:
            if connection:
                connection.close()
    return render_template('register.html', msg=msg)

@app.route('/categories')
def categories():
    user_info = {
        'is_authenticated': 'loggedin' in session,
        'username': session.get('username')
    }
    return render_template('categories.html', user=user_info)

@app.route('/recipes/<category>')
def recipes(category):
    user_info = {
        'is_authenticated': 'loggedin' in session,
        'username': session.get('username')
    }
    
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM Recipe WHERE category = %s', (category,))
            recipes = cursor.fetchall()
    except Exception as e:
        return f"Error fetching recipes: {str(e)}"
    finally:
        if connection:
            connection.close()

    return render_template('recipes.html', recipes=recipes, category=category, user=user_info)

@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    user_info = {
        'is_authenticated': 'loggedin' in session,
        'username': session.get('username')
    }
    
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Get the recipe details and average rating
            cursor.execute(''' 
                SELECT R.*, 
                       (SELECT AVG(value) FROM Rating WHERE Recipe_ID = %s) AS average_rating 
                FROM Recipe R 
                WHERE R.ID = %s
            ''', (recipe_id, recipe_id))
            recipe = cursor.fetchone()

            # Convert average rating to stars (1-5 scale)
            average_rating = recipe[-1]  # Assuming the average rating is the last column
            if average_rating is not None:
                star_rating = round(average_rating)  # Convert to an integer for star representation
            else:
                star_rating = 0  # No ratings

            cursor.execute('SELECT * FROM Comment WHERE Recipe_ID = %s', (recipe_id,))
            comments = cursor.fetchall()

            cursor.execute('SELECT * FROM Nutritional_Info WHERE Recipe_ID = %s', (recipe_id,))
            nutritional_info = cursor.fetchone()

            cursor.execute('SELECT * FROM Ingredient WHERE Recipe_ID = %s', (recipe_id,))
            ingredients = cursor.fetchall()

            cursor.execute('SELECT * FROM Rating WHERE Recipe_ID=%s', (recipe_id,))
            ratings = cursor.fetchall()

    except Exception as e:
        return f"Error fetching recipe: {str(e)}"
    finally:
        if connection:
            connection.close()

    return render_template('view_recipe.html', recipe=recipe, comments=comments, nutritional_info=nutritional_info, ingredients=ingredients, ratings=ratings, star_rating=star_rating, user=user_info)


@app.route('/add_recipe/<category>', methods=['GET', 'POST'])
def add_recipe(category):
    categories = ["Veg", "Non-Veg", "Beverages", "Desserts"]
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        prep_time = int(request.form['prepTime'])  # Convert to integer for calculation
        cook_time = int(request.form['cookTime'])  
        servings = request.form['servings']# Convert to integer for calculation
        total_time = prep_time + cook_time  # Calculate totalTime automatically
        url = request.form.get('url', '')
        course = request.form['course']
        cuisine = request.form['cuisine']
        diet = request.form['diet']
        instructions = request.form['instructions']
        ingredients = request.form['ingredients']
        calories = request.form.get('calories', 0)
        carbs = request.form.get('carbs', 0)
        proteins = request.form.get('proteins', 0)
        fats = request.form.get('fats', 0)
        user_id = session.get('id')

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO Recipe (name, prepTime, cookTime, servings, totalTime, url, category, course, cuisine, diet, instructions, U_id) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (name, prep_time, cook_time, servings, total_time, url, category, course, cuisine, diet, instructions, user_id)
                )
                recipe_id = cursor.lastrowid
                cursor.execute(
                    'INSERT INTO Nutritional_Info (Recipe_ID, Calories, Carbs, Proteins, Fats) VALUES (%s, %s, %s, %s, %s)',
                    (recipe_id, calories, carbs, proteins, fats)
                )
                for ingredient in ingredients.split(','):
                    cursor.execute('INSERT INTO Ingredient (I_name, Recipe_ID) VALUES (%s, %s)', (ingredient.strip(), recipe_id))
                connection.commit()
            return redirect(url_for('recipes', category=category))
        except Exception as e:
            app.logger.error(f"Error adding recipe: {str(e)}")
            return f"Error adding recipe: {str(e)}"
        finally:
            if connection:
                connection.close()

    return render_template('add_recipe.html', categories=categories, category=category)


@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    categories = ["Veg", "Non-Veg", "Beverages", "Desserts"]
    if 'username' not in session:
        return redirect(url_for('login'))

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM Recipe WHERE ID = %s', (recipe_id,))
            recipe = cursor.fetchone()
            if recipe is None:
                return f"Recipe with ID {recipe_id} not found."

            cursor.execute('SELECT * FROM Nutritional_Info WHERE Recipe_ID = %s', (recipe_id,))
            nutritional_info = cursor.fetchone()

            cursor.execute('SELECT I_name FROM Ingredient WHERE Recipe_ID = %s', (recipe_id,))
            ingredients = [row[0] for row in cursor.fetchall()]

        if request.method == 'POST':
            name = request.form['name']
            prep_time = int(request.form['prepTime'])
            cook_time = int(request.form['cookTime'])
            servings = request.form['servings']
            total_time = prep_time + cook_time  # Calculate totalTime automatically
            url = request.form.get('url', '')
            course = request.form['course']
            cuisine = request.form['cuisine']
            diet = request.form['diet']
            instructions = request.form['instructions']
            calories = request.form.get('calories', 0)
            carbs = request.form.get('carbs', 0)
            proteins = request.form.get('proteins', 0)
            fats = request.form.get('fats', 0)

            with connection.cursor() as cursor:
                cursor.execute(
                    'UPDATE Recipe SET name = %s, prepTime = %s, cookTime = %s, servings = %s, totalTime = %s, url = %s, '
                    'course = %s, cuisine = %s, diet = %s, instructions = %s WHERE ID = %s',
                    (name, prep_time, cook_time, servings, total_time, url, course, cuisine, diet, instructions, recipe_id)
                )
                cursor.execute(
                    'UPDATE Nutritional_Info SET Calories = %s, Carbs = %s, Proteins = %s, Fats = %s WHERE Recipe_ID = %s',
                    (calories, carbs, proteins, fats, recipe_id)
                )
                cursor.execute('DELETE FROM Ingredient WHERE Recipe_ID = %s', (recipe_id,))
                for ingredient in request.form.getlist('ingredients'):
                    cursor.execute('INSERT INTO Ingredient (I_name, Recipe_ID) VALUES (%s, %s)', (ingredient.strip(), recipe_id))

                connection.commit()
            return redirect(url_for('recipes', category=recipe[12]))

    except Exception as e:
        app.logger.error(f"Error editing recipe: {str(e)}")
        return f"Error editing recipe: {str(e)}"
    finally:
        if connection:
            connection.close()

    return render_template('edit_recipe.html', categories=categories, recipe=recipe, 
                           nutritional_info=nutritional_info, ingredients=ingredients)



@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Delete related data in other tables
            cursor.execute('DELETE FROM Ingredient WHERE Recipe_ID = %s', (recipe_id,))
            cursor.execute('DELETE FROM Nutritional_Info WHERE Recipe_ID = %s', (recipe_id,))
            cursor.execute('DELETE FROM Comment WHERE Recipe_ID = %s', (recipe_id,))
            cursor.execute('DELETE FROM Rating WHERE Recipe_ID = %s', (recipe_id,))
            
            # Delete the recipe itself
            cursor.execute('DELETE FROM Recipe WHERE ID = %s', (recipe_id,))
            
            connection.commit()
        
        # After deletion, redirect to the categories page or home page
        return redirect(url_for('categories'))
    
    except Exception as e:
        return f"Error deleting recipe: {str(e)}"
    finally:
        if connection:
            connection.close()

@app.route('/comment/<int:recipe_id>', methods=['POST'])
def add_comment(recipe_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    comment = request.form['comment']
    user_id = session.get('id')

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO Comment (text, Recipe_ID, User_ID) VALUES (%s, %s, %s)', (comment, recipe_id, user_id))
            connection.commit()
    except Exception as e:
        return f"Error adding comment: {str(e)}"
    finally:
        if connection:
            connection.close()

    return redirect(url_for('view_recipe', recipe_id=recipe_id))

@app.route('/rate/<int:recipe_id>', methods=['POST'])
def add_rating(recipe_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    rating = request.form['rating']
    user_id = session.get('id')

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO Rating (value, Recipe_ID, User_ID) VALUES (%s, %s, %s)', (rating, recipe_id, user_id))
            connection.commit()
    except Exception as e:
        return f"Error adding rating: {str(e)}"
    finally:
        if connection:
            connection.close()

    return redirect(url_for('view_recipe', recipe_id=recipe_id))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
