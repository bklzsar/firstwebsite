from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from jinja2 import pass_environment
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

app.secret_key="burakblog"  # flash mesajlarını yayımlamak için bunu yapıyoruz 

# Kullanıcı giriş decorator'u
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session["admin_mode"]:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntüleyemezsiniz","danger")   
            return redirect(url_for("server"))
    return decorated_function
# Kullanıcı kayıt formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.length(min = 4,max = 25)])   #validators sınırlama getirir (parola zorunludur vb.)
    username = StringField("Kullanıcı adı", validators=[validators.length(min = 4,max = 35)])   
    email = StringField("Email Adresi",validators=[validators.Email(message= "Lütfen geçerli bir email adresi girin.")])   
    password = PasswordField("Parola", validators=[validators.DataRequired(message= "Lütfen bir parola girin."),validators.EqualTo(fieldname="confirm",message="Parolanız uyuşmuyor")])   
    confirm = PasswordField("Parola doğrula")

# Kullanıcı giriş formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")


# Makale oluşturma formu
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.length(min = 5, max = 100),validators.DataRequired(message ="Başlık girmeniz gerekiyor.")])
    content = TextAreaField("Makale içeriği",validators=[validators.length(min=10)])

# Makale silme formu
@app.route("/delete/<string:id>")
@admin_required

def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "select * from articles where author =%s and id =%s"

    result = cursor.execute(sorgu,(session["username"],id))  # kullanıcı sadece kendi makalelerini silebilir

    if result > 0:
        sorgu2= "delete from articles where id =%s"
        cursor.execute(sorgu2,(id,))

        mysql.connection.commit()

        return redirect(url_for("dashboard"))
        flash("Makaleniz başarıyla silindi","success")

    else:
        flash("Bu işleme yetkiniz yok.","danger")
        return redirect(url_for("server"))

# Makale güncelleme formu
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@admin_required
def update(id):
    if request.method =="GET":
        cursor = mysql.connection.cursor()

        sorgu = "select * from articles where id =%s"

        result = cursor.execute(sorgu,(id,))

        if result > 0:
            article = cursor.fetchone()
            form = ArticleForm()  # İçini article ile dolduracağımız için request eklemiyoruz

            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("update.html",form = form)
        
        else:
            flash("Böyle bir makale bulunmamaktadır","warning")
            return redirect(url_for("server"))
    else:   # Post request kısmı
        
        form = ArticleForm(request.form)

        newtitle = form.title.data
        newcontent = form.content.data

        sorgu2= "Update articles set title =%s, content =%s where id=%s"

        cursor = mysql.connection.cursor()
        
        cursor.execute(sorgu2,(newtitle,newcontent,id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))
        

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "burakblog"

app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)




@app.route("/")
def server():
    return render_template("change.html", answer ="evet",)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles"
    
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()

        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")


@app.route("/article/<string:id>")  # dinamik url yapısı oluşturduk
def article(id):
    cursor = mysql.connection.cursor()

    sorgu = "select * from articles where id = %s"

    result = cursor.execute(sorgu,(id,))
    

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")


@app.route("/register",methods=["GET","POST"])  # Hem get requests hemde post requests alabilir anlamına geliyor
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        
        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"  # ? işareti anlamına geliyor

        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()

        sorgu2 ="select * from users where username = %s"

        result = cursor.execute(sorgu2,(username,))

        session["username"] = name

        if result > 1:
            flash("Bu kullanıcı adı kullanılıyor","danger")
            return redirect(url_for("register"))


        else:
            flash("Başarıyla kayıt oldun " + name,category="success")
            return redirect(url_for("login")) 

    
    else:
        return render_template("register.html",form = form)


    
@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST" and form.validate():
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()


        sorgu = "select * from users where username = %s"

        result = cursor.execute(sorgu,(username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla giriş yaptınız","success")
                session["logged_in"] = True
                session["username"] = username
                if username == "admin":
                    if sha256_crypt.verify(password_entered,real_password):
                        session["admin_mode"] = True
                return redirect(url_for("server"))
            else:
                flash("Kullanıcı adı veya şifre hatalı","danger")
                return redirect(url_for("login"))
    return render_template("login.html",form = form)

@app.route("/logout")
def logout():
    session["logged_in"] = False
    session["admin_mode"] = False
    return render_template("change.html")


@app.route("/dashboard")
@admin_required
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "select * from articles where author =%s"

    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
    
        return render_template("dashboard.html")



@app.route("/addarticle",methods = ["GET","POST"])
@admin_required
def addarticle():
    form = ArticleForm(request.form )
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        
        cursor = mysql.connection.cursor()

        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()

        cursor.close()

        flash("Makale başarıyla eklendi!","success")

        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html",form = form)

# Arama Url

@app.route("/search", methods = ["GET","POST"])
def search():
    if request.method =="GET":
        return redirect(url_for("server"))
    else:
        keyword = request.form.get("keyword") # adını keyword yaptığımız search bilgilerini çekiyoruz get ile

        cursor = mysql.connection.cursor()

        sorgu = "select * from articles where title like '%"+keyword+"%'"
        
        result = cursor.execute(sorgu)

        if result == 0 :
            flash("Aranan kelimeye uygun makale bulunamadı.","warning")
            return redirect(url_for("articles"))

        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)
if __name__ == "__main__":
    app.run(debug=True)

