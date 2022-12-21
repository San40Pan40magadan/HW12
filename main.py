from flask import (
    Flask,
    render_template,
    session,
    make_response,
    redirect,
    abort,
    request,
    session
)
from sqlalchemy.ext.declarative import declarative_base
from loguru import logger
import datetime
import random
import time
from sqlalchemy import (
    String,
    Column,
    Integer,
    DateTime,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import sessionmaker, relationship
from datetime import timedelta


Base = declarative_base()
engine = create_engine(
    "sqlite:///ad.db",
    echo=True,
    connect_args={'check_same_thread': False}
)
Session = sessionmaker(bind=engine)
session_factory = Session()


def create_app():
    app = Flask(__name__)
    return app


app = create_app()


class Ad(Base):
    __tablename__ = "ad"

    id = Column(Integer,  primary_key=True)
    ad_text = Column(String(300))
    created_at = Column(DateTime, default=datetime.datetime.utcnow())
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User")

    @classmethod
    def create(cls, obj_in):
        obj_in_data = dict(obj_in)
        db_obj = Ad(**obj_in_data)
        session_factory.add(db_obj)
        session_factory.commit()
        return obj_in_data

    @classmethod
    def list(cls, *args, **kwargs):
        return session_factory.query(Ad).filter(*args).filter_by(**kwargs).all()

    @classmethod
    def get(cls, *args, **kwargs):
        return session_factory.query(Ad).filter(*args).filter_by(**kwargs).first()

    @classmethod
    def delete(cls, db_obj):
        session_factory.delete(db_obj)
        session_factory.commit()

    @classmethod
    def update(cls, db_obj, obj_in):
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_instance=True)
        for f in obj_in:
            if f in update_data:
                setattr(db_obj, f, update_data[f])
        session_factory.add(db_obj)
        session_factory.commit()
        return db_obj

    def __repr__(self):
        return f"{self.ad_text}"


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)

    @classmethod
    def create(cls, obj_in):
        obj_in_data = dict(obj_in)
        db_obj = User(**obj_in_data)
        session_factory.add(db_obj)
        session_factory.commit()
        return obj_in_data

    @classmethod
    def get(cls, *args, **kwargs):
        return session_factory.query(User).filter(*args).filter_by(**kwargs).first()

    def __repr__(self):
        return f"{self.user_id}"


def generate_user_id():
    return random.randint(1000, 9999)


@app.route("/", methods=["GET"])
def index():
    ads = Ad.list()
    for ad in ads:
        if session.get(f"ad_{ad.id}") is None:
            Ad.delete(db_obj=ad)
    response = make_response(
        render_template(
            "index.html",
            ads=Ad.list()
        )
    )
    if not request.cookies.get("user_id"):
        user_id = generate_user_id()
        response.set_cookie("user_id", value=f"{user_id}")
        User.create(obj_in={"user_id": user_id})
    return response


@app.route('/create', methods=["GET", "POST"])
def create_ad():
    if request.method == "POST":
        text = request.form.get("ad_text")
        logger.info(text)
        user_id = request.cookies.get("user_id")
        logger.info(user_id)
        if not user_id:
            raise abort(403)
        user = User.get(user_id=int(user_id))
        logger.info(user)
        if not text:
            raise abort(404)
        Ad.create({"ad_text": text, "user_id": user.id, "user": user})
        ads = Ad.list()
        for ad in ads:
            if session.get(f"ad_{ad.id}") is None:
                session[f"ad_{ad.id}"] = ad.id
        return redirect('/')
    return render_template('create_ad.html')


@app.route('/delete/<int:ad_id>', methods=['GET'])
def delete_ad(ad_id: int):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise abort(403)
    ad = Ad.get(id=ad_id)
    if ad.user.user_id != int(user_id):
        raise abort(403)
    Ad.delete(db_obj=ad)
    return redirect('/')


@app.route('/edit/<int:ad_id>', methods=['GET', 'POST'])
def edit_ad(ad_id: int):
    ad = Ad.get(id=ad_id)
    if request.method == "POST":
        user_id = request.cookies.get("user_id")
        if not user_id:
            raise abort(403)
        if ad.user.user_id != int(user_id):
            raise abort(403)
        ad_text = request.form.get("ad_text")
        if not ad_text:
            raise abort(404)
        Ad.update(db_obj=ad, obj_in={"ad_text": ad_text})
        return redirect('/')
    return render_template('edit_ad.html', ad=ad)


if __name__ == "__main__":
    # Base.metadata.create_all(engine)
    app.permanent_session_lifetime = timedelta(seconds=30)
    app.secret_key = 'ertetetegetegegedgsghjk'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(host="0.0.0.0", port=5000, debug=True)
    session.permanent = True

