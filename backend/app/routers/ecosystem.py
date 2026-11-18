import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.tournament_models import Tournament, TournamentParticipant
from app.ecosystem_models import (
    Club, ClubMembership, CoachProfile, Product, CartItem, ShopOrder,
    ShopOrderItem, Notification, Conversation, ChatMessage, QrPass, MedalAward,
)

router = APIRouter(tags=["ecosystem"])


def _admin(user: User) -> bool:
    return any(role.role == "admin" for role in user.roles)


def _notify(db: Session, user_id: int, title: str, body: str, category: str):
    db.add(Notification(user_id=user_id, title=title, body=body, category=category))


def _club_or_404(db: Session, club_id: int) -> Club:
    item = db.get(Club, club_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Клуб олдсонгүй.")
    return item


def _can_manage_club(db: Session, club: Club, user: User) -> bool:
    if club.owner_id == user.id or _admin(user):
        return True
    return db.query(ClubMembership.id).filter(
        ClubMembership.club_id == club.id,
        ClubMembership.user_id == user.id,
        ClubMembership.role == "manager",
        ClubMembership.status == "active",
    ).first() is not None


class ClubCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    sport: str = Field(min_length=2, max_length=80)
    region: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=3000)
    contact_phone: str | None = Field(default=None, min_length=8, max_length=24)


class MembershipDecision(BaseModel):
    accepted: bool


class CoachInput(BaseModel):
    club_id: int | None = None
    sport: str = Field(min_length=2, max_length=80)
    qualification: str = Field(min_length=2, max_length=200)
    experience_years: int = Field(default=0, ge=0, le=70)
    specialties: str = Field(default="", max_length=2000)


class ProductInput(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=3000)
    category: str = Field(min_length=2, max_length=80)
    price: int = Field(ge=0, le=2_000_000_000)
    stock: int = Field(ge=0, le=1_000_000)


class CartInput(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=100)


class CheckoutInput(BaseModel):
    delivery_address: str = Field(min_length=5, max_length=300)
    contact_phone: str = Field(min_length=8, max_length=24)


class QrIssueInput(BaseModel):
    purpose: str = Field(min_length=2, max_length=40)
    reference_type: str = Field(min_length=2, max_length=30)
    reference_id: int = Field(gt=0)
    owner_id: int | None = None
    expires_in_minutes: int = Field(default=60, ge=1, le=10080)


class QrVerifyInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class MedalInput(BaseModel):
    participant_id: int
    medal: str = Field(pattern="^(gold|silver|bronze)$")
    points: int = Field(default=0, ge=0, le=10000)


class ConversationInput(BaseModel):
    other_user_id: int


class MessageInput(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


@router.post("/clubs", status_code=201)
def create_club(payload: ClubCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = Club(
        owner_id=user.id, name=payload.name.strip(), sport=payload.sport.strip(),
        region=payload.region.strip(), description=payload.description.strip(),
        contact_phone=payload.contact_phone, verification_status="pending",
    )
    db.add(club)
    db.flush()
    db.add(ClubMembership(club_id=club.id, user_id=user.id, role="owner", status="active"))
    db.commit()
    db.refresh(club)
    return {"id": club.id, "name": club.name, "sport": club.sport, "region": club.region,
            "description": club.description, "owner_id": club.owner_id,
            "verification_status": club.verification_status, "created_at": club.created_at}


@router.get("/clubs")
def list_clubs(
    sport: str | None = Query(default=None, max_length=80),
    region: str | None = Query(default=None, max_length=120),
    search: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    query = db.query(Club).filter(Club.verification_status == "verified")
    if sport:
        query = query.filter(Club.sport.ilike(f"%{sport.strip()}%"))
    if region:
        query = query.filter(Club.region.ilike(f"%{region.strip()}%"))
    if search:
        query = query.filter(Club.name.ilike(f"%{search.strip()}%"))
    return [{"id": x.id, "name": x.name, "sport": x.sport, "region": x.region,
             "description": x.description, "verification_status": x.verification_status}
            for x in query.order_by(Club.name).limit(200).all()]


@router.get("/clubs/mine")
def my_clubs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Club).filter(Club.owner_id == user.id).order_by(Club.created_at.desc()).all()
    return [{"id": x.id, "name": x.name, "sport": x.sport, "region": x.region,
             "verification_status": x.verification_status} for x in rows]


@router.post("/clubs/{club_id}/join", status_code=201)
def join_club(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = _club_or_404(db, club_id)
    if club.verification_status != "verified":
        raise HTTPException(status_code=409, detail="Зөвхөн баталгаажсан клубт элсэх хүсэлт илгээнэ.")
    existing = db.query(ClubMembership).filter_by(club_id=club.id, user_id=user.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Та энэ клубт хүсэлт илгээсэн эсвэл гишүүн болсон байна.")
    item = ClubMembership(club_id=club.id, user_id=user.id, role="athlete", status="pending")
    db.add(item)
    _notify(db, club.owner_id, "Клубын шинэ хүсэлт", f"{user.phone} клубт элсэх хүсэлт илгээлээ.", "club")
    db.commit()
    return {"id": item.id, "club_id": club.id, "status": item.status}


@router.get("/clubs/{club_id}/members")
def club_members(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = _club_or_404(db, club_id)
    if not _can_manage_club(db, club, user):
        raise HTTPException(status_code=403, detail="Зөвхөн клубын удирдлага гишүүдийг харна.")
    rows = db.query(ClubMembership).filter(ClubMembership.club_id == club.id).order_by(ClubMembership.created_at.desc()).all()
    return [{"id": x.id, "user_id": x.user_id, "role": x.role, "status": x.status, "created_at": x.created_at}
            for x in rows]


@router.post("/clubs/{club_id}/members/{membership_id}/decision")
def decide_membership(club_id: int, membership_id: int, payload: MembershipDecision,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = _club_or_404(db, club_id)
    if not _can_manage_club(db, club, user):
        raise HTTPException(status_code=403, detail="Клубын эзэмшигч эсвэл админ шаардлагатай.")
    item = db.query(ClubMembership).filter_by(id=membership_id, club_id=club.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Гишүүнчлэлийн хүсэлт олдсонгүй.")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Энэ хүсэлтэд өмнө нь хариу өгсөн байна.")
    item.status = "active" if payload.accepted else "rejected"
    if payload.accepted:
        _notify(db, item.user_id, "Клубын хүсэлт зөвшөөрөгдлөө", f"{club.name} клубт элсэх хүсэлт баталгаажлаа.", "club")
    db.commit()
    return {"id": item.id, "status": item.status}


@router.post("/coaches/profile")
def upsert_coach_profile(payload: CoachInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.club_id is not None:
        club = _club_or_404(db, payload.club_id)
        if not _can_manage_club(db, club, user):
            raise HTTPException(status_code=403, detail="Энэ клубт дасгалжуулагч холбох эрхгүй.")
    item = db.query(CoachProfile).filter_by(user_id=user.id).first()
    values = payload.model_dump()
    if item is None:
        item = CoachProfile(user_id=user.id, **values, verification_status="pending")
        db.add(item)
    else:
        for key, value in values.items():
            setattr(item, key, value)
        item.verification_status = "pending"
    db.commit()
    db.refresh(item)
    return {"id": item.id, "user_id": item.user_id, "club_id": item.club_id, "sport": item.sport,
            "qualification": item.qualification, "experience_years": item.experience_years,
            "specialties": item.specialties, "verification_status": item.verification_status}


@router.get("/coaches")
def list_coaches(sport: str | None = None, region: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CoachProfile).filter(CoachProfile.verification_status == "verified")
    if sport:
        query = query.filter(CoachProfile.sport.ilike(f"%{sport.strip()}%"))
    rows = query.order_by(CoachProfile.experience_years.desc()).limit(200).all()
    result = []
    for x in rows:
        club = db.get(Club, x.club_id) if x.club_id else None
        if region and (club is None or region.lower() not in club.region.lower()):
            continue
        result.append({"id": x.id, "user_id": x.user_id, "club_id": x.club_id, "club_name": club.name if club else None,
                       "sport": x.sport, "qualification": x.qualification, "experience_years": x.experience_years,
                       "specialties": x.specialties})
    return result


@router.post("/store/products", status_code=201)
def create_product(payload: ProductInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = Product(seller_id=user.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "title": item.title, "category": item.category, "price": item.price,
            "stock": item.stock, "active": item.active}


@router.get("/store/products")
def list_products(category: str | None = None, search: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Product).filter(Product.active.is_(True), Product.stock > 0)
    if category:
        query = query.filter(Product.category.ilike(f"%{category.strip()}%"))
    if search:
        query = query.filter(Product.title.ilike(f"%{search.strip()}%"))
    return [{"id": x.id, "title": x.title, "description": x.description, "category": x.category,
             "price": x.price, "stock": x.stock, "seller_id": x.seller_id}
            for x in query.order_by(Product.created_at.desc()).limit(200).all()]


@router.post("/store/cart")
def add_to_cart(payload: CartInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if product is None or not product.active:
        raise HTTPException(status_code=404, detail="Бараа олдсонгүй.")
    if payload.quantity > product.stock:
        raise HTTPException(status_code=409, detail="Үлдэгдэл хүрэлцэхгүй байна.")
    item = db.query(CartItem).filter_by(user_id=user.id, product_id=product.id).first()
    if item:
        if item.quantity + payload.quantity > product.stock:
            raise HTTPException(status_code=409, detail="Сагсны тоо үлдэгдлээс их байна.")
        item.quantity += payload.quantity
    else:
        item = CartItem(user_id=user.id, product_id=product.id, quantity=payload.quantity)
        db.add(item)
    db.commit()
    return {"product_id": product.id, "quantity": item.quantity}


@router.get("/store/cart")
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    result, total = [], 0
    for row in rows:
        product = db.get(Product, row.product_id)
        if product is None:
            continue
        line = product.price * row.quantity
        total += line
        result.append({"product_id": product.id, "title": product.title, "price": product.price,
                       "quantity": row.quantity, "line_total": line, "stock": product.stock})
    return {"items": result, "total_amount": total}


@router.post("/store/checkout", status_code=201)
def checkout(payload: CheckoutInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    if not rows:
        raise HTTPException(status_code=400, detail="Сагс хоосон байна.")
    locked = []
    total = 0
    for row in rows:
        product = db.query(Product).filter(Product.id == row.product_id).with_for_update().first()
        if product is None or not product.active or product.stock < row.quantity:
            raise HTTPException(status_code=409, detail="Сагсан дахь барааны үлдэгдэл өөрчлөгдсөн байна.")
        locked.append((row, product))
        total += product.price * row.quantity
    order = ShopOrder(user_id=user.id, total_amount=total, delivery_address=payload.delivery_address.strip(),
                      contact_phone=payload.contact_phone.strip(), status="pending_payment")
    db.add(order)
    db.flush()
    for row, product in locked:
        db.add(ShopOrderItem(order_id=order.id, product_id=product.id, product_title=product.title,
                             unit_price=product.price, quantity=row.quantity))
        product.stock -= row.quantity
        db.delete(row)
        _notify(db, product.seller_id, "Шинэ захиалга", f"{product.title} бараанд шинэ захиалга үүслээ.", "order")
    db.commit()
    db.refresh(order)
    return {"id": order.id, "total_amount": order.total_amount, "status": order.status,
            "delivery_address": order.delivery_address, "created_at": order.created_at,
            "payment_note": "Төлбөрийн онлайн интеграц одоогоор холбогдоогүй."}


@router.get("/store/orders")
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ShopOrder).filter(ShopOrder.user_id == user.id).order_by(ShopOrder.created_at.desc()).limit(100).all()
    return [{"id": x.id, "total_amount": x.total_amount, "status": x.status,
             "delivery_address": x.delivery_address, "created_at": x.created_at} for x in rows]


@router.get("/notifications")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return [{"id": x.id, "title": x.title, "body": x.body, "category": x.category,
             "is_read": x.read_at is not None, "created_at": x.created_at} for x in rows]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Мэдэгдэл олдсонгүй.")
    item.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": item.id, "is_read": True}


def _conversation_for_user(db: Session, conversation_id: int, user_id: int) -> Conversation:
    item = db.get(Conversation, conversation_id)
    if item is None or user_id not in (item.participant_low_id, item.participant_high_id):
        raise HTTPException(status_code=404, detail="Харилцан яриа олдсонгүй.")
    return item


@router.post("/chat/conversations", status_code=201)
def create_conversation(payload: ConversationInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.other_user_id == user.id or db.get(User, payload.other_user_id) is None:
        raise HTTPException(status_code=400, detail="Харилцах хэрэглэгчийн дугаар буруу байна.")
    low, high = sorted((user.id, payload.other_user_id))
    item = db.query(Conversation).filter_by(participant_low_id=low, participant_high_id=high).first()
    if item is None:
        item = Conversation(participant_low_id=low, participant_high_id=high)
        db.add(item)
        try:
            db.commit()
            db.refresh(item)
        except IntegrityError:
            db.rollback()
            item = db.query(Conversation).filter_by(participant_low_id=low, participant_high_id=high).first()
    return {"id": item.id, "other_user_id": high if user.id == low else low, "created_at": item.created_at}


@router.get("/chat/conversations")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Conversation).filter(or_(Conversation.participant_low_id == user.id,
                                              Conversation.participant_high_id == user.id)).order_by(Conversation.created_at.desc()).all()
    result = []
    for x in rows:
        other = x.participant_high_id if x.participant_low_id == user.id else x.participant_low_id
        last = db.query(ChatMessage).filter_by(conversation_id=x.id).order_by(ChatMessage.created_at.desc()).first()
        result.append({"id": x.id, "other_user_id": other, "last_message": last.body if last else None,
                       "created_at": x.created_at})
    return result


@router.get("/chat/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _conversation_for_user(db, conversation_id, user.id)
    rows = db.query(ChatMessage).filter_by(conversation_id=conversation_id).order_by(ChatMessage.created_at.asc()).limit(500).all()
    for row in rows:
        if row.sender_id != user.id and row.read_at is None:
            row.read_at = datetime.now(timezone.utc)
    db.commit()
    return [{"id": x.id, "sender_id": x.sender_id, "body": x.body,
             "is_read": x.read_at is not None, "created_at": x.created_at} for x in rows]


@router.post("/chat/conversations/{conversation_id}/messages", status_code=201)
def send_message(conversation_id: int, payload: MessageInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = _conversation_for_user(db, conversation_id, user.id)
    item = ChatMessage(conversation_id=conversation.id, sender_id=user.id, body=payload.body.strip())
    recipient = conversation.participant_high_id if conversation.participant_low_id == user.id else conversation.participant_low_id
    db.add(item)
    _notify(db, recipient, "Шинэ зурвас", payload.body.strip()[:250], "chat")
    db.commit()
    db.refresh(item)
    return {"id": item.id, "conversation_id": item.conversation_id, "sender_id": item.sender_id,
            "body": item.body, "created_at": item.created_at}


@router.post("/qr/passes", status_code=201)
def issue_qr_pass(payload: QrIssueInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owner_id = payload.owner_id or user.id
    if owner_id != user.id and not _admin(user):
        raise HTTPException(status_code=403, detail="Өөр хэрэглэгчид QR олгох эрхгүй.")
    if payload.reference_type == "competition":
        tournament = db.get(Tournament, payload.reference_id)
        if tournament is None or (tournament.organizer_id != user.id and not _admin(user)):
            raise HTTPException(status_code=403, detail="Тэмцээний QR үүсгэх эрхгүй.")
    elif payload.reference_type == "club":
        club = _club_or_404(db, payload.reference_id)
        if not _can_manage_club(db, club, user):
            raise HTTPException(status_code=403, detail="Клубын QR үүсгэх эрхгүй.")
    token = secrets.token_urlsafe(32)
    item = QrPass(token_hash=hashlib.sha256(token.encode()).hexdigest(), owner_id=owner_id,
                  issued_by=user.id, purpose=payload.purpose, reference_type=payload.reference_type,
                  reference_id=payload.reference_id,
                  expires_at=datetime.now(timezone.utc) + timedelta(minutes=payload.expires_in_minutes))
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "token": token, "qr_payload": token, "purpose": item.purpose,
            "reference_type": item.reference_type, "reference_id": item.reference_id,
            "expires_at": item.expires_at, "single_use": True}


@router.post("/qr/verify")
def verify_qr_pass(payload: QrVerifyInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    item = db.query(QrPass).filter_by(token_hash=token_hash).with_for_update().first()
    if item is None:
        raise HTTPException(status_code=404, detail="QR код хүчингүй байна.")
    now = datetime.now(timezone.utc)
    expires = item.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        raise HTTPException(status_code=410, detail="QR кодын хугацаа дууссан байна.")
    if item.used_at is not None:
        raise HTTPException(status_code=409, detail="Энэ QR код өмнө нь ашиглагдсан байна.")
    allowed = _admin(user)
    if item.reference_type == "competition":
        tournament = db.get(Tournament, item.reference_id)
        allowed = allowed or (tournament is not None and tournament.organizer_id == user.id)
    elif item.reference_type == "club":
        club = db.get(Club, item.reference_id)
        allowed = allowed or (club is not None and _can_manage_club(db, club, user))
    else:
        # Generic passes (for example, a personal fitness entry) remain
        # verifiable by the original issuer; resource-backed passes require
        # the verifier to retain current management rights.
        allowed = allowed or user.id == item.issued_by
    if not allowed:
        raise HTTPException(status_code=403, detail="Энэ QR кодыг баталгаажуулах эрхгүй.")
    # Claim the pass atomically. A read-then-write check alone can allow two
    # concurrent scanners to accept the same token on databases without row locks.
    claimed = db.query(QrPass).filter(
        QrPass.id == item.id,
        QrPass.used_at.is_(None),
        QrPass.expires_at > now,
    ).update({QrPass.used_at: now}, synchronize_session=False)
    if claimed != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="Энэ QR код өмнө нь ашиглагдсан эсвэл хугацаа нь дууссан байна.")
    _notify(db, item.owner_id, "QR бүртгэл баталгаажлаа", f"{item.purpose} эрх амжилттай шалгагдлаа.", "qr")
    db.commit()
    return {"valid": True, "used": True, "purpose": item.purpose, "reference_type": item.reference_type,
            "reference_id": item.reference_id, "owner_id": item.owner_id, "checked_at": now}


@router.post("/competitions/{tournament_id}/medals", status_code=201)
def award_medal(tournament_id: int, payload: MedalInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tournament = db.get(Tournament, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=404, detail="Тэмцээн олдсонгүй.")
    if tournament.organizer_id != user.id and not _admin(user):
        raise HTTPException(status_code=403, detail="Зөвхөн зохион байгуулагч медаль баталгаажуулна.")
    participant = db.query(TournamentParticipant).filter_by(id=payload.participant_id, tournament_id=tournament_id).first()
    if participant is None:
        raise HTTPException(status_code=404, detail="Тэмцээний оролцогч олдсонгүй.")
    existing = db.query(MedalAward).filter_by(tournament_id=tournament_id, participant_id=participant.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Энэ тамирчинд медаль өмнө нь бүртгэгдсэн байна.")
    item = MedalAward(tournament_id=tournament_id, participant_id=participant.id, medal=payload.medal,
                      points=payload.points, awarded_by=user.id)
    db.add(item)
    _notify(db, participant.user_id, "Тэмцээний медаль", f"{tournament.title}: {payload.medal} медаль авлаа.", "medal") if participant.user_id else None
    db.commit()
    db.refresh(item)
    return {"id": item.id, "tournament_id": item.tournament_id, "participant_id": item.participant_id,
            "athlete": participant.full_name, "club": participant.club_name, "medal": item.medal,
            "points": item.points, "created_at": item.created_at}


@router.get("/competitions/{tournament_id}/medals")
def list_medals(tournament_id: int, db: Session = Depends(get_db)):
    if db.get(Tournament, tournament_id) is None:
        raise HTTPException(status_code=404, detail="Тэмцээн олдсонгүй.")
    rows = db.query(MedalAward, TournamentParticipant).join(
        TournamentParticipant, TournamentParticipant.id == MedalAward.participant_id
    ).filter(MedalAward.tournament_id == tournament_id).order_by(MedalAward.points.desc()).all()
    return [{"id": award.id, "participant_id": athlete.id, "athlete": athlete.full_name,
             "club": athlete.club_name, "medal": award.medal, "points": award.points}
            for award, athlete in rows]


@router.get("/leaderboards/medals")
def medal_leaderboard(sport: str | None = None, db: Session = Depends(get_db)):
    query = db.query(TournamentParticipant.club_name,
                     func.sum(case((MedalAward.medal == "gold", 1), else_=0)).label("gold"),
                     func.sum(case((MedalAward.medal == "silver", 1), else_=0)).label("silver"),
                     func.sum(case((MedalAward.medal == "bronze", 1), else_=0)).label("bronze"),
                     func.sum(MedalAward.points).label("points")).join(
        MedalAward, MedalAward.participant_id == TournamentParticipant.id
    ).join(Tournament, Tournament.id == MedalAward.tournament_id)
    if sport:
        query = query.filter(Tournament.sport.ilike(f"%{sport.strip()}%"))
    rows = query.group_by(TournamentParticipant.club_name).order_by(func.sum(MedalAward.points).desc()).limit(100).all()
    return [{"club": row[0] or "Бие даасан", "gold": int(row[1] or 0), "silver": int(row[2] or 0),
             "bronze": int(row[3] or 0), "points": int(row[4] or 0)} for row in rows]


@router.get("/admin/analytics")
def admin_analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _admin(user):
        raise HTTPException(status_code=403, detail="Админ эрх шаардлагатай.")
    return {
        "users": db.query(User).count(),
        "clubs": db.query(Club).count(),
        "coaches": db.query(CoachProfile).count(),
        "competitions": db.query(Tournament).count(),
        "participants": db.query(TournamentParticipant).count(),
        "medals": db.query(MedalAward).count(),
        "products": db.query(Product).count(),
        "orders": db.query(ShopOrder).count(),
        "pending_club_verifications": db.query(Club).filter_by(verification_status="pending").count(),
        "pending_coach_verifications": db.query(CoachProfile).filter_by(verification_status="pending").count(),
        "unread_notifications": db.query(Notification).filter(Notification.read_at.is_(None)).count(),
        "messages": db.query(ChatMessage).count(),
    }


class VerificationInput(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=1000)


class OrderStatusInput(BaseModel):
    status: str = Field(pattern="^(confirmed|shipped|delivered|cancelled)$")


@router.post("/admin/clubs/{club_id}/verify")
def verify_club(club_id: int, payload: VerificationInput,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _admin(user):
        raise HTTPException(status_code=403, detail="Админ эрх шаардлагатай.")
    club = _club_or_404(db, club_id)
    club.verification_status = "verified" if payload.approved else "rejected"
    if payload.approved:
        _notify(db, club.owner_id, "Клуб баталгаажлаа", f"{club.name} клуб баталгаажсан.", "club")
    db.commit()
    return {"id": club.id, "verification_status": club.verification_status}


@router.post("/admin/coaches/{user_id}/verify")
def verify_coach(user_id: int, payload: VerificationInput,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _admin(user):
        raise HTTPException(status_code=403, detail="Админ эрх шаардлагатай.")
    coach = db.query(CoachProfile).filter_by(user_id=user_id).first()
    if coach is None:
        raise HTTPException(status_code=404, detail="Дасгалжуулагчийн профайл олдсонгүй.")
    coach.verification_status = "verified" if payload.approved else "rejected"
    if payload.approved:
        _notify(db, coach.user_id, "Дасгалжуулагчийн эрх баталгаажлаа", "Таны мэргэжлийн мэдээлэл баталгаажлаа.", "coach")
    db.commit()
    return {"user_id": coach.user_id, "verification_status": coach.verification_status}


@router.get("/store/seller/orders")
def seller_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order_ids = db.query(ShopOrderItem.order_id).join(
        Product, Product.id == ShopOrderItem.product_id
    ).filter(Product.seller_id == user.id).distinct().subquery()
    rows = db.query(ShopOrder).filter(ShopOrder.id.in_(select(order_ids.c.order_id))).order_by(ShopOrder.created_at.desc()).limit(200).all()
    result = []
    for order in rows:
        items = db.query(ShopOrderItem).join(Product, Product.id == ShopOrderItem.product_id).filter(
            ShopOrderItem.order_id == order.id, Product.seller_id == user.id
        ).all()
        result.append({"id": order.id, "total_amount": sum(x.unit_price * x.quantity for x in items),
                       "status": order.status, "items": [{"title": x.product_title, "quantity": x.quantity} for x in items],
                       "created_at": order.created_at})
    return result


@router.post("/store/orders/{order_id}/status")
def update_seller_order_status(order_id: int, payload: OrderStatusInput,
                               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.get(ShopOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй.")
    items = db.query(ShopOrderItem).filter_by(order_id=order.id).all()
    products = [db.get(Product, x.product_id) for x in items if x.product_id is not None]
    if not products or any(product is None or product.seller_id != user.id for product in products):
        raise HTTPException(status_code=403, detail="Энэ захиалгын бүх бараа таны дэлгүүрт хамаарахгүй.")
    transitions = {
        "pending_payment": {"confirmed", "cancelled"},
        "confirmed": {"shipped", "cancelled"},
        "shipped": {"delivered"},
    }
    if payload.status not in transitions.get(order.status, set()):
        raise HTTPException(status_code=409, detail="Захиалгын төлөвийн шилжилт зөвшөөрөгдөхгүй.")
    if payload.status == "cancelled":
        for line in items:
            if line.product_id is not None:
                product = db.get(Product, line.product_id)
                if product is not None:
                    product.stock += line.quantity
    order.status = payload.status
    _notify(db, order.user_id, "Захиалгын төлөв шинэчлэгдлээ", f"Захиалга #{order.id}: {payload.status}", "order")
    db.commit()
    return {"id": order.id, "status": order.status}


class ClubUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    sport: str | None = Field(default=None, min_length=2, max_length=80)
    region: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=3000)
    contact_phone: str | None = Field(default=None, min_length=8, max_length=24)


class MembershipRoleInput(BaseModel):
    role: str = Field(pattern="^(athlete|coach|manager)$")


class ProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=3000)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    price: int | None = Field(default=None, ge=0, le=2_000_000_000)
    stock: int | None = Field(default=None, ge=0, le=1_000_000)
    active: bool | None = None


@router.patch("/clubs/{club_id}")
def update_club(club_id: int, payload: ClubUpdate,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = _club_or_404(db, club_id)
    if not _can_manage_club(db, club, user):
        raise HTTPException(status_code=403, detail="Клубын эзэмшигч эсвэл админ шаардлагатай.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip()
        setattr(club, key, value)
    club.verification_status = "pending"
    db.commit()
    db.refresh(club)
    return {"id": club.id, "name": club.name, "sport": club.sport, "region": club.region,
            "verification_status": club.verification_status}


@router.post("/clubs/{club_id}/members/{membership_id}/role")
def update_membership_role(club_id: int, membership_id: int, payload: MembershipRoleInput,
                           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = _club_or_404(db, club_id)
    if not _can_manage_club(db, club, user):
        raise HTTPException(status_code=403, detail="Клубын эзэмшигч эсвэл админ шаардлагатай.")
    membership = db.query(ClubMembership).filter_by(id=membership_id, club_id=club.id, status="active").first()
    if membership is None:
        raise HTTPException(status_code=404, detail="Идэвхтэй гишүүн олдсонгүй.")
    if membership.role == "owner":
        raise HTTPException(status_code=409, detail="Клубын эзэмшигчийн эрхийг энэ үйлдлээр өөрчлөхгүй.")
    membership.role = payload.role
    db.commit()
    return {"id": membership.id, "role": membership.role}


@router.delete("/clubs/{club_id}/members/{membership_id}")
def remove_club_member(club_id: int, membership_id: int,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = _club_or_404(db, club_id)
    if not _can_manage_club(db, club, user):
        raise HTTPException(status_code=403, detail="Клубын эзэмшигч эсвэл админ шаардлагатай.")
    membership = db.query(ClubMembership).filter_by(id=membership_id, club_id=club.id).first()
    if membership is None:
        raise HTTPException(status_code=404, detail="Гишүүн олдсонгүй.")
    if membership.role == "owner":
        raise HTTPException(status_code=409, detail="Клубын эзэмшигчийг устгах боломжгүй.")
    db.delete(membership)
    db.commit()
    return {"deleted": True}


@router.get("/coaches/mine")
def my_coach_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(CoachProfile).filter_by(user_id=user.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Дасгалжуулагчийн профайл үүсгээгүй байна.")
    return {"id": item.id, "user_id": item.user_id, "club_id": item.club_id, "sport": item.sport,
            "qualification": item.qualification, "experience_years": item.experience_years,
            "specialties": item.specialties, "verification_status": item.verification_status}


@router.patch("/store/products/{product_id}")
def update_product(product_id: int, payload: ProductUpdate,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Бараа олдсонгүй.")
    if product.seller_id != user.id and not _admin(user):
        raise HTTPException(status_code=403, detail="Зөвхөн барааны эзэмшигч засварлана.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return {"id": product.id, "title": product.title, "price": product.price,
            "stock": product.stock, "active": product.active}


@router.delete("/store/cart/{product_id}")
def remove_cart_item(product_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(CartItem).filter_by(user_id=user.id, product_id=product_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Сагсны бараа олдсонгүй.")
    db.delete(item)
    db.commit()
    return {"deleted": True}
