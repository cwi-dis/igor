from flask_wtf import FlaskForm
from flask_codemirror.fields import CodeMirrorField
from wtforms.fields import SubmitField
from flask import Flask, render_template, request
from flask_codemirror import CodeMirror



# mandatory
CODEMIRROR_LANGUAGES = ['python', 'html']
WTF_CSRF_ENABLED = True
SECRET_KEY = 'secret'
# optional
CODEMIRROR_THEME = '3024-day'
CODEMIRROR_ADDONS = (
        ('ADDON_DIR','ADDON_NAME'),
)
app = Flask(__name__)
app.config.from_object(__name__)
codemirror = CodeMirror(app)

class MyForm(FlaskForm):
    source_code = CodeMirrorField(language='python', config={'lineNumbers': 'true'})
    submit = SubmitField('Submit')

@app.route('/', methods = ['GET', 'POST'])
def index():
    form = MyForm()
    if form.validate_on_submit():
        text = form.source_code.data
        sourceCode = request.form['sourceCode']
        print(text)
    return render_template('index.html', form=form)

# check for the main app loop
if __name__ == "__main__":
    app.run(debug=True)