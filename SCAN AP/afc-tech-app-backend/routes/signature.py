from flask import Blueprint, request, jsonify
from models import Job, JobSignature
from db import db

signature_bp = Blueprint("signature", __name__)


@signature_bp.route("/jobs/<int:job_id>/signature", methods=["POST"])
def create_signature(job_id):
    data = request.json or {}
    signature_data = data.get("signature_data")
    signer_name = data.get("signer_name")
    signer_role = data.get("signer_role")

    if not signature_data:
        return jsonify({"error": "Signature required"}), 400

    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.signature:
        return jsonify({"error": "Job already signed"}), 409

    sig = JobSignature(
        job_id=job.id,
        signer_name=signer_name,
        signer_role=signer_role,
        signature_data=signature_data,
    )
    db.session.add(sig)
    db.session.commit()
    return jsonify({"message": "Signature saved", "id": sig.id}), 201
