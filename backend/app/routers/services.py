from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.service_models import ServiceProvider, ServiceRequest
from app.service_schemas import (
    ServiceProviderInput,
    ServiceProviderOutput,
    ServiceRequestDecision,
    ServiceRequestInput,
    ServiceRequestResponse,
    ServiceVerificationInput,
)

router = APIRouter(prefix="/services", tags=["services"])

SERVICE_CATEGORIES = [
    {"slug": "coach", "name": "Дасгалжуулагч", "description": "Хувийн болон багийн бэлтгэл, сургалтын хөтөлбөр."},
    {"slug": "sports_doctor", "name": "Спортын эмч", "description": "Спортын үзлэг, зөвлөгөө, цаг захиалга."},
    {"slug": "strength_specialist", "name": "Хүчний мэргэжилтэн", "description": "Хүч, хурд, тэсрэлттэй хүчний бэлтгэл."},
    {"slug": "sports_psychologist", "name": "Сэтгэл зүйч", "description": "Тамирчны төвлөрөл, тэмцээний сэтгэл зүй."},
    {"slug": "sports_nutritionist", "name": "Хоол зүйч", "description": "Спортын хооллолт, жингийн зохицуулалт."},
    {"slug": "physiotherapist", "name": "Хөдөлгөөн засалч", "description": "Хөдөлгөөн засал, нөхөн сэргээх үйлчилгээ."},
    {"slug": "sports_analyst", "name": "Спортын шинжээч", "description": "Тамирчин, багийн үзүүлэлт, статистик шинжилгээ."},
    {"slug": "venue_booking", "name": "Заал захиалга", "description": "Спортын заал, талбайн мэдээлэл, захиалгын хүсэлт."},
    {"slug": "sports_store", "name": "Спорт бараа худалдаа", "description": "Спортын хувцас, хэрэгсэл, барааны үйлчилгээ."},
    {"slug": "clubs_training", "name": "Сургалт, клубууд", "description": "Клуб, секц, сургалтын элсэлт, хуваарь."},
]


def _is_admin(user: User) -> bool:
    return any(role.role == "admin" for role in user.roles)


def _provider_output(item: ServiceProvider) -> ServiceProviderOutput:
    return ServiceProviderOutput(
        id=item.id,
        user_id=item.user_id,
        category=item.category,
        display_name=item.display_name,
        description=item.description,
        sport=item.sport,
        region=item.region,
        price_from=item.price_from,
        credentials=item.credentials,
        verification_status=item.verification_status,
        verified_at=item.verified_at,
        created_at=item.created_at,
    )


def _request_output(item: ServiceRequest) -> ServiceRequestResponse:
    return ServiceRequestResponse(
        id=item.id,
        requester_id=item.requester_id,
        provider_user_id=item.provider_user_id,
        category=item.category,
        title=item.title,
        details=item.details,
        sport=item.sport,
        region=item.region,
        preferred_at=item.preferred_at,
        contact_phone=item.contact_phone,
        status=item.status,
        payment_status=item.payment_status,
        response_note=item.response_note,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/categories")
def list_service_categories():
    return SERVICE_CATEGORIES


@router.get("/providers", response_model=list[ServiceProviderOutput])
def list_service_providers(
    category: str = Query(min_length=2, max_length=60),
    sport: str | None = Query(default=None, max_length=80),
    region: str | None = Query(default=None, max_length=120),
    search: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    query = db.query(ServiceProvider).filter(
        ServiceProvider.category == category,
        ServiceProvider.verification_status == "verified",
    )
    if sport:
        query = query.filter(ServiceProvider.sport.ilike(f"%{sport}%"))
    if region:
        query = query.filter(ServiceProvider.region.ilike(f"%{region}%"))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(
            ServiceProvider.display_name.ilike(pattern),
            ServiceProvider.description.ilike(pattern),
            ServiceProvider.credentials.ilike(pattern),
        ))
    rows = query.order_by(ServiceProvider.created_at.desc()).limit(100).all()
    return [_provider_output(item) for item in rows]


@router.get("/providers/me", response_model=ServiceProviderOutput)
def get_my_service_provider(
    category: str = Query(min_length=2, max_length=60),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ServiceProvider).filter(
        ServiceProvider.user_id == user.id,
        ServiceProvider.category == category,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Энэ төрлийн үйлчилгээ үзүүлэгчийн профайл бүртгэгдээгүй байна.")
    return _provider_output(item)


@router.post("/providers/me", response_model=ServiceProviderOutput, status_code=201)
def save_my_service_provider(
    payload: ServiceProviderInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ServiceProvider).filter(
        ServiceProvider.user_id == user.id,
        ServiceProvider.category == payload.category,
    ).first()
    if item is None:
        item = ServiceProvider(user_id=user.id, **payload.model_dump(), verification_status="pending")
        db.add(item)
    else:
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        # Changes to service identity or credentials require a new review.
        item.verification_status = "pending"
        item.verified_at = None
        item.verified_by = None
        item.verification_note = None
    db.commit()
    db.refresh(item)
    return _provider_output(item)


@router.get("/providers/pending", response_model=list[ServiceProviderOutput])
def list_service_provider_reviews(
    verification_status: str = Query(default="pending", pattern="^(pending|verified|rejected)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Зөвхөн админ үйлчилгээ үзүүлэгчийн бүртгэл шалгана.")
    rows = db.query(ServiceProvider).filter(
        ServiceProvider.verification_status == verification_status
    ).order_by(ServiceProvider.created_at.asc()).limit(200).all()
    return [_provider_output(item) for item in rows]


@router.post("/providers/{provider_id}/verify", response_model=ServiceProviderOutput)
def verify_service_provider(
    provider_id: int,
    payload: ServiceVerificationInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Зөвхөн админ үйлчилгээ үзүүлэгчийг баталгаажуулна.")
    item = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Үйлчилгээ үзүүлэгч олдсонгүй.")
    item.verification_status = "verified" if payload.approved else "rejected"
    item.verification_note = payload.note
    item.verified_at = datetime.now(timezone.utc) if payload.approved else None
    item.verified_by = user.id
    db.commit()
    db.refresh(item)
    return _provider_output(item)


@router.post("/requests", response_model=ServiceRequestResponse, status_code=201)
def create_service_request(
    payload: ServiceRequestInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = None
    if payload.provider_user_id is not None:
        provider = db.query(ServiceProvider).filter(
            ServiceProvider.user_id == payload.provider_user_id,
            ServiceProvider.category == payload.category,
            ServiceProvider.verification_status == "verified",
        ).first()
        if provider is None:
            raise HTTPException(status_code=404, detail="Баталгаажсан үйлчилгээ үзүүлэгч олдсонгүй.")
        if provider.user_id == user.id:
            raise HTTPException(status_code=400, detail="Өөрийн үйлчилгээ рүү хүсэлт илгээх боломжгүй.")
    item = ServiceRequest(
        requester_id=user.id,
        provider_user_id=provider.user_id if provider else None,
        category=payload.category,
        title=payload.title,
        details=payload.details,
        sport=payload.sport,
        region=payload.region,
        preferred_at=payload.preferred_at,
        contact_phone=payload.contact_phone,
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _request_output(item)


@router.get("/requests/me", response_model=list[ServiceRequestResponse])
def list_my_service_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(ServiceRequest).filter(
        or_(
            ServiceRequest.requester_id == user.id,
            ServiceRequest.provider_user_id == user.id,
        )
    ).order_by(ServiceRequest.created_at.desc()).limit(100).all()
    return [_request_output(item) for item in rows]


@router.post("/requests/{request_id}/respond", response_model=ServiceRequestResponse)
def respond_to_service_request(
    request_id: int,
    payload: ServiceRequestDecision,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Хүсэлт олдсонгүй.")
    if item.provider_user_id != user.id and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Энэ хүсэлтэд хариу өгөх эрхгүй.")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Зөвхөн хүлээгдэж буй хүсэлтэд хариу өгнө.")
    item.status = "accepted" if payload.accepted else "rejected"
    item.response_note = payload.note
    db.commit()
    db.refresh(item)
    return _request_output(item)


@router.post("/requests/{request_id}/cancel", response_model=ServiceRequestResponse)
def cancel_service_request(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Хүсэлт олдсонгүй.")
    if item.requester_id != user.id and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Зөвхөн хүсэлт гаргагч хүсэлтээ цуцална.")
    if item.status not in {"pending", "accepted"}:
        raise HTTPException(status_code=409, detail="Энэ хүсэлтийг цуцлах боломжгүй.")
    item.status = "cancelled"
    db.commit()
    db.refresh(item)
    return _request_output(item)


@router.post("/requests/{request_id}/complete", response_model=ServiceRequestResponse)
def complete_service_request(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Хүсэлт олдсонгүй.")
    if user.id not in {item.requester_id, item.provider_user_id} and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Энэ хүсэлтийг дуусгах эрхгүй.")
    if item.status != "accepted":
        raise HTTPException(status_code=409, detail="Зөвхөн зөвшөөрсөн хүсэлтийг дуусгана.")
    item.status = "completed"
    db.commit()
    db.refresh(item)
    return _request_output(item)
