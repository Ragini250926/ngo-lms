from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app=Flask(__name__)
app.config['SECRET_KEY']='ngo-learn-demo-secret'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///ngo_learn.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120),nullable=False); email=db.Column(db.String(150),unique=True,nullable=False); password_hash=db.Column(db.String(255),nullable=False); role=db.Column(db.String(30),default='volunteer'); organisation=db.Column(db.String(180),default=''); active=db.Column(db.Boolean,default=True); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Course(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(180),nullable=False); description=db.Column(db.Text,nullable=False); category=db.Column(db.String(100),default='General'); difficulty=db.Column(db.String(50),default='Beginner'); duration=db.Column(db.String(50),default='2 hours'); instructor=db.Column(db.String(120),default='NGO Learn Team'); published=db.Column(db.Boolean,default=True)
class Enrollment(db.Model):
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); course_id=db.Column(db.Integer,db.ForeignKey('course.id'),nullable=False); enrolled_at=db.Column(db.DateTime,default=datetime.utcnow); user=db.relationship('User'); course=db.relationship('Course'); __table_args__=(db.UniqueConstraint('user_id','course_id'),)
class Module(db.Model):
    id=db.Column(db.Integer,primary_key=True); course_id=db.Column(db.Integer,db.ForeignKey('course.id'),nullable=False); title=db.Column(db.String(180),nullable=False); description=db.Column(db.Text,default=''); order_no=db.Column(db.Integer,default=1); course=db.relationship('Course',backref=db.backref('modules',cascade='all,delete-orphan'))
class Material(db.Model):
    id=db.Column(db.Integer,primary_key=True); module_id=db.Column(db.Integer,db.ForeignKey('module.id'),nullable=False); title=db.Column(db.String(180),nullable=False); material_type=db.Column(db.String(30),default='text'); content=db.Column(db.Text,default=''); resource_url=db.Column(db.String(500),default=''); module=db.relationship('Module',backref=db.backref('materials',cascade='all,delete-orphan'))
class Quiz(db.Model):
    id=db.Column(db.Integer,primary_key=True); course_id=db.Column(db.Integer,db.ForeignKey('course.id'),nullable=False); title=db.Column(db.String(180),nullable=False); passing_percentage=db.Column(db.Integer,default=60); course=db.relationship('Course',backref=db.backref('quizzes',cascade='all,delete-orphan'))
class Question(db.Model):
    id=db.Column(db.Integer,primary_key=True); quiz_id=db.Column(db.Integer,db.ForeignKey('quiz.id'),nullable=False); text=db.Column(db.Text,nullable=False); a=db.Column(db.String(300),nullable=False); b=db.Column(db.String(300),nullable=False); c=db.Column(db.String(300),nullable=False); d=db.Column(db.String(300),nullable=False); correct=db.Column(db.String(1),nullable=False); quiz=db.relationship('Quiz',backref=db.backref('questions',cascade='all,delete-orphan'))
class Result(db.Model):
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); quiz_id=db.Column(db.Integer,db.ForeignKey('quiz.id'),nullable=False); score=db.Column(db.Integer); total=db.Column(db.Integer); percentage=db.Column(db.Float); passed=db.Column(db.Boolean); attempted_at=db.Column(db.DateTime,default=datetime.utcnow); user=db.relationship('User'); quiz=db.relationship('Quiz')
class Progress(db.Model):
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); module_id=db.Column(db.Integer,db.ForeignKey('module.id'),nullable=False); completed=db.Column(db.Boolean,default=False); completed_at=db.Column(db.DateTime); __table_args__=(db.UniqueConstraint('user_id','module_id'),)
class Certificate(db.Model):
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); course_id=db.Column(db.Integer,db.ForeignKey('course.id'),nullable=False); certificate_id=db.Column(db.String(80),unique=True); issued_at=db.Column(db.DateTime,default=datetime.utcnow); user=db.relationship('User'); course=db.relationship('Course')

def user(): return db.session.get(User,session.get('user_id')) if session.get('user_id') else None
def req(view):
    @wraps(view)
    def w(*a,**k):
        if not user(): flash('Please login first.','warning'); return redirect(url_for('login'))
        return view(*a,**k)
    return w
def admin(view):
    @wraps(view)
    def w(*a,**k):
        if not user() or user().role!='admin': flash('Admin access required.','danger'); return redirect(url_for('login'))
        return view(*a,**k)
    return w
def pct(uid,cid):
    ms=Module.query.filter_by(course_id=cid).all(); done=Progress.query.join(Module).filter(Progress.user_id==uid,Progress.completed==True,Module.course_id==cid).count()
    return round(done/len(ms)*100) if ms else 0
def completed(uid,cid):
    qs=Quiz.query.filter_by(course_id=cid).all(); qok=all(Result.query.filter_by(user_id=uid,quiz_id=q.id,passed=True).first() for q in qs)
    return pct(uid,cid)==100 and qok
def issue(uid,cid):
    if completed(uid,cid) and not Certificate.query.filter_by(user_id=uid,course_id=cid).first():
        db.session.add(Certificate(user_id=uid,course_id=cid,certificate_id=f'NGOL-{datetime.utcnow():%Y%m%d}-{uid:03d}-{cid:03d}')); db.session.commit()

@app.context_processor
def globals(): return {'logged_user':user(),'course_progress':pct,'course_completed':completed}

@app.route('/')
def home(): return render_template('index.html',courses=Course.query.filter_by(published=True).limit(6).all())
@app.route('/about')
def about(): return render_template('about.html')
@app.route('/features')
def features(): return render_template('features.html')
@app.route('/ngo')
def ngo(): return render_template('ngo.html')
@app.route('/training')
def training(): return render_template('training.html')
@app.route('/contact')
def contact(): return render_template('contact.html')
@app.route('/research')
def research(): return render_template('research.html')
@app.route('/survey')
def survey(): return render_template('survey.html')
@app.route('/courses')
def courses():
    q=request.args.get('q',''); cat=request.args.get('category',''); query=Course.query.filter_by(published=True)
    if q: query=query.filter(Course.title.ilike(f'%{q}%'))
    if cat: query=query.filter_by(category=cat)
    return render_template('courses.html',courses=query.all(),categories=[x[0] for x in db.session.query(Course.category).distinct()],q=q,category=cat)
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['name'].strip(); email=request.form['email'].strip().lower(); pw=request.form['password']; role=request.form.get('role','volunteer')
        if User.query.filter_by(email=email).first(): flash('Email already registered.','warning'); return render_template('register.html')
        db.session.add(User(name=name,email=email,password_hash=generate_password_hash(pw),role=role,organisation=request.form.get('organisation','').strip())); db.session.commit(); flash('Registration successful.','success'); return redirect(url_for('login'))
    return render_template('register.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if u and u.active and check_password_hash(u.password_hash,request.form['password']):
            session.clear(); session['user_id']=u.id; return redirect(url_for('admin_dashboard' if u.role=='admin' else 'dashboard'))
        flash('Invalid login details.','danger')
    return render_template('login.html')
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/dashboard')
@req
def dashboard():
    es=Enrollment.query.filter_by(user_id=user().id).all(); return render_template('dashboard.html',enrollments=es,completed=[e for e in es if completed(user().id,e.course_id)],certificates=Certificate.query.filter_by(user_id=user().id).count(),results=Result.query.filter_by(user_id=user().id).order_by(Result.attempted_at.desc()).limit(5).all())
@app.route('/my-courses')
@req
def my_courses(): return render_template('my_courses.html',enrollments=Enrollment.query.filter_by(user_id=user().id).all())
@app.route('/course/<int:cid>')
def course(cid):
    c=db.get_or_404(Course,cid); u=user(); e=Enrollment.query.filter_by(user_id=u.id,course_id=cid).first() if u else None; return render_template('course_details.html',course=c,enrolled=e,modules=Module.query.filter_by(course_id=cid).order_by(Module.order_no).all())
@app.route('/course/<int:cid>/enroll',methods=['POST'])
@req
def enroll(cid):
    if not Enrollment.query.filter_by(user_id=user().id,course_id=cid).first(): db.session.add(Enrollment(user_id=user().id,course_id=cid)); db.session.commit(); flash('Enrolled successfully.','success')
    return redirect(url_for('course',cid=cid))
@app.route('/module/<int:mid>')
@req
def module(mid):
    m=db.get_or_404(Module,mid); e=Enrollment.query.filter_by(user_id=user().id,course_id=m.course_id).first()
    if not e: abort(403)
    return render_template('learning_material.html',module=m,progress=Progress.query.filter_by(user_id=user().id,module_id=mid).first())
@app.route('/module/<int:mid>/complete',methods=['POST'])
@req
def complete_module(mid):
    m=db.get_or_404(Module,mid); p=Progress.query.filter_by(user_id=user().id,module_id=mid).first()
    if not p: p=Progress(user_id=user().id,module_id=mid,completed=True,completed_at=datetime.utcnow()); db.session.add(p)
    else: p.completed=True; p.completed_at=datetime.utcnow()
    db.session.commit(); issue(user().id,m.course_id); return redirect(url_for('course',cid=m.course_id))
@app.route('/quiz/<int:qid>',methods=['GET','POST'])
@req
def quiz(qid):
    qz=db.get_or_404(Quiz,qid); qs=qz.questions
    if request.method=='POST':
        score=sum(request.form.get(f'q{x.id}')==x.correct for x in qs); total=len(qs); per=round(score/total*100,2) if total else 0; passed=per>=qz.passing_percentage
        r=Result(user_id=user().id,quiz_id=qz.id,score=score,total=total,percentage=per,passed=passed); db.session.add(r); db.session.commit();
        if passed: issue(user().id,qz.course_id)
        return render_template('quiz_result.html',quiz=qz,result=r)
    return render_template('quiz.html',quiz=qz,questions=qs)
@app.route('/progress')
@req
def progress():
    es=Enrollment.query.filter_by(user_id=user().id).all(); return render_template('progress.html',enrollments=es)
@app.route('/certificates')
@req
def certificates(): return render_template('certificates.html',certificates=Certificate.query.filter_by(user_id=user().id).all())
@app.route('/certificate/<int:cid>')
@req
def certificate(cid):
    c=db.get_or_404(Certificate,cid)
    if c.user_id!=user().id and user().role!='admin': abort(403)
    return render_template('certificate.html',certificate=c)
@app.route('/profile',methods=['GET','POST'])
@req
def profile():
    if request.method=='POST': user().name=request.form['name']; user().organisation=request.form.get('organisation',''); db.session.commit(); flash('Profile updated.','success')
    return render_template('profile.html',profile=user())

@app.route('/admin')
@admin
def admin_dashboard(): return render_template('admin/dashboard.html',users=User.query.all(),total_users=User.query.count(),staff=User.query.filter_by(role='staff').count(),volunteers=User.query.filter_by(role='volunteer').count(),courses=Course.query.count(),certificates=Certificate.query.count(),results=Result.query.order_by(Result.attempted_at.desc()).limit(8).all())
@app.route('/admin/users')
@admin
def admin_users(): return render_template('admin/users.html',users=User.query.all())
@app.route('/admin/users/toggle/<int:uid>',methods=['POST'])
@admin
def toggle_user(uid): u=db.get_or_404(User,uid); u.active=not u.active; db.session.commit(); return redirect(url_for('admin_users'))
@app.route('/admin/courses')
@admin
def admin_courses(): return render_template('admin/courses.html',courses=Course.query.all())
@app.route('/admin/course/new',methods=['GET','POST'])
@app.route('/admin/course/<int:cid>/edit',methods=['GET','POST'])
@admin
def course_form(cid=None):
    c=db.session.get(Course,cid) if cid else Course()
    if request.method=='POST':
        c.title=request.form['title']; c.description=request.form['description']; c.category=request.form.get('category','General'); c.difficulty=request.form.get('difficulty','Beginner'); c.duration=request.form.get('duration','2 hours'); c.instructor=request.form.get('instructor','NGO Learn Team'); c.published=bool(request.form.get('published'))
        if not cid: db.session.add(c)
        db.session.commit(); return redirect(url_for('admin_courses'))
    return render_template('admin/course_form.html',course=c)
@app.route('/admin/course/<int:cid>/delete',methods=['POST'])
@admin
def delete_course(cid): db.session.delete(db.get_or_404(Course,cid)); db.session.commit(); return redirect(url_for('admin_courses'))
@app.route('/admin/course/<int:cid>/modules',methods=['GET','POST'])
@admin
def admin_modules(cid):
    c=db.get_or_404(Course,cid)
    if request.method=='POST': db.session.add(Module(course_id=cid,title=request.form['title'],description=request.form.get('description',''),order_no=int(request.form.get('order_no',1)))); db.session.commit()
    return render_template('admin/modules.html',course=c,modules=Module.query.filter_by(course_id=cid).order_by(Module.order_no).all())
@app.route('/admin/module/<int:mid>/materials',methods=['GET','POST'])
@admin
def materials(mid):
    m=db.get_or_404(Module,mid)
    if request.method=='POST': db.session.add(Material(module_id=mid,title=request.form['title'],material_type=request.form.get('material_type','text'),content=request.form.get('content',''),resource_url=request.form.get('resource_url',''))); db.session.commit()
    return render_template('admin/materials.html',module=m)
@app.route('/admin/quizzes',methods=['GET','POST'])
@admin
def admin_quizzes():
    if request.method=='POST': db.session.add(Quiz(course_id=int(request.form['course_id']),title=request.form['title'],passing_percentage=int(request.form.get('passing_percentage',60)))); db.session.commit()
    return render_template('admin/quizzes.html',quizzes=Quiz.query.all(),courses=Course.query.all())
@app.route('/admin/quiz/<int:qid>/questions',methods=['GET','POST'])
@admin
def questions(qid):
    qz=db.get_or_404(Quiz,qid)
    if request.method=='POST': db.session.add(Question(quiz_id=qid,text=request.form['text'],a=request.form['a'],b=request.form['b'],c=request.form['c'],d=request.form['d'],correct=request.form['correct'])); db.session.commit()
    return render_template('admin/quiz_questions.html',quiz=qz)
@app.route('/admin/reports')
@admin
def reports(): return render_template('admin/reports.html',enrollments=Enrollment.query.all(),results=Result.query.all(),certificates=Certificate.query.all())
@app.route('/admin/certificates')
@admin
def admin_certs(): return render_template('admin/certificates.html',certificates=Certificate.query.all())


def seed():
    if User.query.count()==0:
        db.session.add_all([User(name='Alex Morgan',email='admin@ngolearn.local',password_hash=generate_password_hash('Admin@123'),role='admin',organisation='NGO Learn Demo'),User(name='Samira Khan',email='staff@ngolearn.local',password_hash=generate_password_hash('Staff@123'),role='staff',organisation='Hope Community Centre'),User(name='Rohan Mehta',email='volunteer@ngolearn.local',password_hash=generate_password_hash('Volunteer@123'),role='volunteer',organisation='Care & Serve Trust')]); db.session.commit()
    if Course.query.count()==0:
        names=[('NGO Volunteer Orientation','Volunteer Development'),('Community Outreach & Engagement','Community Work'),('Child Safety & Protection','Safeguarding'),('Elder Care Basics','Elder Care'),('First Aid & Emergency Awareness','Safety'),('Communication Skills','Soft Skills'),('Fundraising & Donor Management','Management'),('Digital Skills for NGOs','Digital Skills'),('Basic Cyber Safety','Digital Safety'),('Volunteer Management','Management'),('Safeguarding & Workplace Safety','Safeguarding'),('Mental Wellbeing & Compassionate Care','Wellbeing')]
        for title,cat in names: db.session.add(Course(title=title,description=f'Practical introductory training for {title.lower()}.',category=cat,duration='2–3 hours'))
        db.session.commit()
        for c in Course.query.all():
            for i,t in enumerate(['Introduction','Practical Skills','Review & Activity'],1): db.session.add(Module(course_id=c.id,title=f'{t} — {c.title}',description='Demo learning module.',order_no=i))
        db.session.commit()
        c=Course.query.filter_by(title='Elder Care Basics').first(); q=Quiz(course_id=c.id,title='Elder Care Basics Assessment'); db.session.add(q); db.session.commit()
        for text,a,b,cx,d,co in [('Which principle should guide care?','Respect and dignity','Ignore preferences','Rush tasks','Share private information','A'),('Which habit improves communication?','Active listening','Interrupting','Avoiding questions','Using unclear language','A'),('What is appropriate in an emergency?','Get appropriate professional help','Post online','Guess treatment','Leave the person alone','A')]: db.session.add(Question(quiz_id=q.id,text=text,a=a,b=b,c=cx,d=d,correct=co))
        db.session.commit()
    v=User.query.filter_by(email='volunteer@ngolearn.local').first(); c=Course.query.filter_by(title='Elder Care Basics').first()
    if v and c and not Enrollment.query.filter_by(user_id=v.id,course_id=c.id).first(): db.session.add(Enrollment(user_id=v.id,course_id=c.id)); db.session.commit()
with app.app_context(): db.create_all(); seed()
if __name__=='__main__': app.run(debug=True)
