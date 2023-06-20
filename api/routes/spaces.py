from app import app, socketio
from models import db
from models.in_space import InSpace
from models.space import Space
from flask import request
from util.user_space_id import (
    with_user_id,
    with_space_id,
    decode_space_id,
    encode_space_id,
    new_space_id,
    space_member,
    get_user_id,
)
from util.response import json_response
from flask_socketio import join_room, leave_room, rooms
from sqlalchemy import delete


@socketio.on("space-move", namespace="/spid")
def listen_on_space(body):
    print(body)
    # Unsubscribe from updates on all spaces
    for room_id in rooms(namespace="/spid"):
        if room_id != request.sid:
            leave_room(room_id)
    # Subscribe to updates on relevant spaces
    if "spid" in body and isinstance(body["spid"], str):
        # Decode space identifier
        try:
            space_id = decode_space_id(body["spid"])
        except ValueError:
            return
        # TODO: verify room membership
        join_room(body["spid"], namespace="/spid")


@app.route("/api/space/get-all", methods=["GET"])
@with_user_id
def list_spaces(user_id):
    spaces_query = db.select(
        Space.display_name, Space.space_id, InSpace.is_owner
    ).where(InSpace.user_id == user_id, InSpace.space_id == Space.space_id)
    spaces = db.session.execute(spaces_query).all()
    return json_response(
        [
            {
                "id": encode_space_id(s.space_id),
                "display_name": s.display_name,
                "owned": s.is_owner,
            }
            for s in spaces
        ]
    )


@app.route("/api/space/join", methods=["PUT"])
@with_user_id
def join_space(user_id):
    body = request.get_json()
    if "id" not in body or not isinstance(body["id"], str):
        return "Bad Request", 400

    try:
        space_id = decode_space_id(body["id"])
    except ValueError:
        return "Bad Request", 400

    space_exists = (
        db.session.execute(db.select(Space).where(Space.space_id == space_id))
        .scalars()
        .one_or_none()
        is not None
    )
    if not space_exists:
        return "File Not Found", 404

    user_in_space = (
        db.session.execute(
            db.select(InSpace).where(
                InSpace.space_id == space_id, InSpace.user_id == user_id
            )
        )
        .scalars()
        .first()
    )
    if user_in_space:
        return "", 204

    db.session.add(InSpace(user_id=user_id, space_id=space_id, is_owner=False))
    db.session.commit()
    return "", 204


@app.route("/api/space/new", methods=["POST"])
@with_user_id
def new_space(user_id):
    body = request.get_json()
    if "display_name" not in body or not isinstance(body["display_name"], str):
        return "Bad Request", 400

    display_name = body["display_name"]
    space_id = new_space_id()

    db.session.add(Space(space_id=space_id, display_name=display_name))
    db.session.add(InSpace(user_id=user_id, space_id=space_id, is_owner=True))
    db.session.commit()
    return json_response({"id": encode_space_id(space_id)})


@app.route("/api/space/name", methods=["GET"])
@with_space_id
def display_name_for_space(space_id):
    display_name = (
        db.session.execute(
            db.select(Space.display_name).where(Space.space_id == space_id)
        )
        .scalars()
        .one_or_none()
    )
    if display_name is None:
        return "File Not Found", 404
    return json_response({"display_name": display_name})


@app.route("/api/space/delete", methods=["DELETE"])
@with_user_id
def delete_space(user_id):
    body = request.get_json()

    if "id" not in body or not isinstance(body["id"], str):
        return "Bad Request", 400

    try:
        space_id = decode_space_id(body["id"])
    except ValueError:
        return "Bad Request", 400

    in_space = (
        db.session.execute(
            db.select(InSpace).where(
                InSpace.user_id == user_id, InSpace.space_id == space_id
            )
        )
        .scalars()
        .one_or_none()
    )
    if in_space is None:
        return "File Not Found", 404
    elif not in_space.is_owner:
        return "Forbidden", 403

    db.session.execute(delete(InSpace).where(InSpace.space_id == space_id))
    db.session.delete(in_space)
    db.session.commit()

    return "", 204
