from datetime import datetime, timedelta, timezone
import hashlib
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import User, UserRole
from app.ecosystem_models import QrPass


def register(client, phone):
    response = client.post("/api/v1/auth/register", json={
        "phone": phone,
        "password": "secure-test-password",
    })
    assert response.status_code == 201
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


def grant_admin(user_id):
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        user.roles.append(UserRole(role="admin"))
        db.commit()
    finally:
        db.close()


def suffix():
    return str(uuid.uuid4().int % 1000000).zfill(6)


def test_club_membership_and_coach_verification_workflow():
    with TestClient(app) as client:
        owner, owner_id = register(client, "+97691" + suffix() + "01")
        athlete, _ = register(client, "+97691" + suffix() + "02")
        manager, _ = register(client, "+97691" + suffix() + "04")
        admin, admin_id = register(client, "+97691" + suffix() + "03")
        grant_admin(admin_id)

        created = client.post("/api/v1/clubs", headers=owner, json={
            "name": "ARENA Judo Club", "sport": "Жүдо", "region": "Улаанбаатар",
            "description": "Тестийн клубын мэдээлэл", "contact_phone": "+97699112233",
        })
        assert created.status_code == 201
        club_id = created.json()["id"]

        pending_join = client.post(f"/api/v1/clubs/{club_id}/join", headers=athlete)
        assert pending_join.status_code == 409
        club_verified = client.post(f"/api/v1/admin/clubs/{club_id}/verify", headers=admin,
                                    json={"approved": True})
        assert club_verified.status_code == 200

        joined = client.post(f"/api/v1/clubs/{club_id}/join", headers=athlete)
        assert joined.status_code == 201
        membership_id = joined.json()["id"]

        decision = client.post(
            f"/api/v1/clubs/{club_id}/members/{membership_id}/decision",
            headers=owner, json={"accepted": True},
        )
        assert decision.status_code == 200
        assert decision.json()["status"] == "active"

        manager_join = client.post(f"/api/v1/clubs/{club_id}/join", headers=manager)
        assert manager_join.status_code == 201
        manager_membership_id = manager_join.json()["id"]
        manager_accepted = client.post(
            f"/api/v1/clubs/{club_id}/members/{manager_membership_id}/decision",
            headers=owner, json={"accepted": True},
        )
        assert manager_accepted.status_code == 200
        promoted = client.post(
            f"/api/v1/clubs/{club_id}/members/{manager_membership_id}/role",
            headers=owner, json={"role": "manager"},
        )
        assert promoted.status_code == 200
        assert client.get(f"/api/v1/clubs/{club_id}/members", headers=manager).status_code == 200
        manager_update = client.patch(
            f"/api/v1/clubs/{club_id}", headers=manager,
            json={"description": "Менежерийн эрхийн шалгалт"},
        )
        assert manager_update.status_code == 200
        denied_athlete_update = client.patch(
            f"/api/v1/clubs/{club_id}", headers=athlete,
            json={"description": "Эрхгүй өөрчлөлт"},
        )
        assert denied_athlete_update.status_code == 403
        reverified = client.post(
            f"/api/v1/admin/clubs/{club_id}/verify", headers=admin,
            json={"approved": True},
        )
        assert reverified.status_code == 200

        coach = client.post("/api/v1/coaches/profile", headers=owner, json={
            "club_id": club_id, "sport": "Жүдо", "qualification": "Дасгалжуулагчийн үнэмлэх",
            "experience_years": 6, "specialties": "Өсвөрийн тамирчдын бэлтгэл",
        })
        assert coach.status_code == 200
        verified = client.post(f"/api/v1/admin/coaches/{owner_id}/verify", headers=admin,
                               json={"approved": True, "note": "Баримт шалгасан"})
        assert verified.status_code == 200
        assert verified.json()["verification_status"] == "verified"
        public = client.get("/api/v1/clubs")
        assert any(item["id"] == club_id for item in public.json())
        coaches = client.get("/api/v1/coaches", params={"sport": "Жүдо"})
        assert any(item["user_id"] == owner_id for item in coaches.json())


def test_qr_pass_is_single_use_and_permission_checked():
    with TestClient(app) as client:
        owner, _ = register(client, "+97692" + suffix() + "01")
        other, _ = register(client, "+97692" + suffix() + "02")
        issued = client.post("/api/v1/qr/passes", headers=owner, json={
            "purpose": "fitness_entry", "reference_type": "fitness_pass",
            "reference_id": 23, "expires_in_minutes": 20,
        })
        assert issued.status_code == 201
        token = issued.json()["token"]
        db = SessionLocal()
        try:
            stored_pass = db.query(QrPass).filter_by(
                token_hash=hashlib.sha256(token.encode()).hexdigest()
            ).one()
            assert stored_pass.token_hash != token
            assert stored_pass.used_at is None
        finally:
            db.close()

        denied = client.post("/api/v1/qr/verify", headers=other, json={"token": token})
        assert denied.status_code == 403

        verified = client.post("/api/v1/qr/verify", headers=owner, json={"token": token})
        assert verified.status_code == 200
        assert verified.json()["valid"] is True

        replay = client.post("/api/v1/qr/verify", headers=owner, json={"token": token})
        assert replay.status_code == 409


def test_store_cart_checkout_stock_and_seller_order_lifecycle():
    with TestClient(app) as client:
        seller, _ = register(client, "+97693" + suffix() + "01")
        buyer, _ = register(client, "+97693" + suffix() + "02")

        product = client.post("/api/v1/store/products", headers=seller, json={
            "title": "Жүдогийн бүс", "description": "Тэмцээний бүс",
            "category": "Эдлэл", "price": 25000, "stock": 8,
        })
        assert product.status_code == 201
        product_id = product.json()["id"]

        added = client.post("/api/v1/store/cart", headers=buyer, json={
            "product_id": product_id, "quantity": 2,
        })
        assert added.status_code == 200
        cart = client.get("/api/v1/store/cart", headers=buyer)
        assert cart.json()["total_amount"] == 50000

        checkout = client.post("/api/v1/store/checkout", headers=buyer, json={
            "delivery_address": "Улаанбаатар хот, Баянзүрх дүүрэг",
            "contact_phone": "+97699112244",
        })
        assert checkout.status_code == 201
        order_id = checkout.json()["id"]
        assert checkout.json()["total_amount"] == 50000

        orders = client.get("/api/v1/store/seller/orders", headers=seller)
        assert any(item["id"] == order_id for item in orders.json())

        for status in ("confirmed", "shipped", "delivered"):
            changed = client.post(f"/api/v1/store/orders/{order_id}/status",
                                  headers=seller, json={"status": status})
            assert changed.status_code == 200
            assert changed.json()["status"] == status

        buyer_orders = client.get("/api/v1/store/orders", headers=buyer)
        assert buyer_orders.json()[0]["status"] == "delivered"


def test_chat_notifications_and_private_conversation_access():
    with TestClient(app) as client:
        sender, _ = register(client, "+97694" + suffix() + "01")
        recipient, _ = register(client, "+97694" + suffix() + "02")
        stranger, _ = register(client, "+97694" + suffix() + "03")
        recipient_id = client.get("/api/v1/auth/me", headers=recipient).json()["id"]

        conversation = client.post("/api/v1/chat/conversations", headers=sender,
                                   json={"other_user_id": recipient_id})
        assert conversation.status_code == 201
        conversation_id = conversation.json()["id"]

        sent = client.post(f"/api/v1/chat/conversations/{conversation_id}/messages",
                           headers=sender, json={"body": "Сайн байна уу?"})
        assert sent.status_code == 201

        received = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages",
                              headers=recipient)
        assert received.status_code == 200
        assert received.json()[0]["body"] == "Сайн байна уу?"

        denied = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages",
                            headers=stranger)
        assert denied.status_code == 404

        notifications = client.get("/api/v1/notifications", headers=recipient)
        assert any(item["category"] == "chat" for item in notifications.json())
        notification_id = next(item["id"] for item in notifications.json() if item["category"] == "chat")
        marked = client.post(f"/api/v1/notifications/{notification_id}/read", headers=recipient)
        assert marked.status_code == 200
        assert marked.json()["is_read"] is True


def test_medal_awards_leaderboard_and_admin_analytics():
    with TestClient(app) as client:
        organizer, organizer_id = register(client, "+97695" + suffix() + "01")
        athlete, _ = register(client, "+97695" + suffix() + "02")
        admin, admin_id = register(client, "+97695" + suffix() + "03")
        grant_admin(admin_id)

        starts_at = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
        tournament = client.post("/api/v1/competitions", headers=organizer, json={
            "title": "ARENA 360 медалийн тест", "sport": "Жүдо",
            "format": "single_elimination", "region": "Улаанбаатар",
            "venue": "Спорт ордон", "starts_at": starts_at, "max_participants": 8,
        })
        assert tournament.status_code == 201
        tournament_id = tournament.json()["id"]

        registered = client.post(f"/api/v1/competitions/{tournament_id}/register",
                                 headers=athlete, json={
            "full_name": "Медалийн тест тамирчин", "club_name": "ARENA Club",
            "contact_phone": "+97696123456",
        })
        assert registered.status_code == 201
        participant_id = registered.json()["id"]

        award = client.post(f"/api/v1/competitions/{tournament_id}/medals",
                            headers=organizer, json={
            "participant_id": participant_id, "medal": "gold", "points": 10,
        })
        assert award.status_code == 201
        medals = client.get(f"/api/v1/competitions/{tournament_id}/medals")
        assert medals.status_code == 200
        assert medals.json()[0]["medal"] == "gold"

        leaderboard = client.get("/api/v1/leaderboards/medals", params={"sport": "Жүдо"})
        assert leaderboard.status_code == 200
        assert any(item["club"] == "ARENA Club" and item["gold"] == 1 for item in leaderboard.json())

        forbidden = client.get("/api/v1/admin/analytics", headers=athlete)
        assert forbidden.status_code == 403
        analytics = client.get("/api/v1/admin/analytics", headers=admin)
        assert analytics.status_code == 200
        assert analytics.json()["medals"] >= 1
        assert analytics.json()["clubs"] >= 0

def test_store_owner_permissions_and_cancelled_order_restores_stock():
    with TestClient(app) as client:
        seller, _ = register(client, "+97696" + suffix() + "01")
        buyer, _ = register(client, "+97696" + suffix() + "02")
        stranger, _ = register(client, "+97696" + suffix() + "03")

        product = client.post("/api/v1/store/products", headers=seller, json={
            "title": "Тестийн жүдогийн цүнх", "description": "Эзэмшлийн шалгалт",
            "category": "Цүнх", "price": 42000, "stock": 5,
        })
        assert product.status_code == 201
        product_id = product.json()["id"]

        denied_edit = client.patch(f"/api/v1/store/products/{product_id}", headers=stranger, json={
            "price": 1, "stock": 999,
        })
        assert denied_edit.status_code == 403

        client.post("/api/v1/store/cart", headers=buyer, json={
            "product_id": product_id, "quantity": 2,
        })
        checkout = client.post("/api/v1/store/checkout", headers=buyer, json={
            "delivery_address": "Улаанбаатар хот, Сүхбаатар дүүрэг",
            "contact_phone": "+97699112255",
        })
        assert checkout.status_code == 201
        order_id = checkout.json()["id"]

        denied_status = client.post(f"/api/v1/store/orders/{order_id}/status",
                                    headers=stranger, json={"status": "confirmed"})
        assert denied_status.status_code == 403

        cancelled = client.post(f"/api/v1/store/orders/{order_id}/status",
                                headers=seller, json={"status": "cancelled"})
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        products = client.get("/api/v1/store/products")
        stored = next(item for item in products.json() if item["id"] == product_id)
        assert stored["stock"] == 5

        repeated_cancel = client.post(f"/api/v1/store/orders/{order_id}/status",
                                      headers=seller, json={"status": "cancelled"})
        assert repeated_cancel.status_code == 409


def test_notification_read_is_scoped_to_authenticated_user():
    with TestClient(app) as client:
        sender, _ = register(client, "+97697" + suffix() + "01")
        recipient, _ = register(client, "+97697" + suffix() + "02")
        stranger, _ = register(client, "+97697" + suffix() + "03")
        recipient_id = client.get("/api/v1/auth/me", headers=recipient).json()["id"]

        conversation = client.post("/api/v1/chat/conversations", headers=sender,
                                   json={"other_user_id": recipient_id})
        assert conversation.status_code == 201
        sent = client.post(
            f"/api/v1/chat/conversations/{conversation.json()['id']}/messages",
            headers=sender, json={"body": "Эрхийн шалгалтын мэдэгдэл"},
        )
        assert sent.status_code == 201

        notifications = client.get("/api/v1/notifications", headers=recipient)
        notification_id = next(
            item["id"] for item in notifications.json() if item["category"] == "chat"
        )
        denied = client.post(
            f"/api/v1/notifications/{notification_id}/read", headers=stranger
        )
        assert denied.status_code == 404

        allowed = client.post(
            f"/api/v1/notifications/{notification_id}/read", headers=recipient
        )
        assert allowed.status_code == 200



def test_qr_pass_expiry_is_enforced():
    with TestClient(app) as client:
        owner, _ = register(client, "+97698" + suffix() + "01")
        issued = client.post("/api/v1/qr/passes", headers=owner, json={
            "purpose": "fitness_entry", "reference_type": "fitness_pass",
            "reference_id": 24, "expires_in_minutes": 5,
        })
        assert issued.status_code == 201
        token = issued.json()["token"]

        db = SessionLocal()
        try:
            stored_pass = db.query(QrPass).filter_by(
                token_hash=hashlib.sha256(token.encode()).hexdigest()
            ).one()
            stored_pass.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        expired = client.post("/api/v1/qr/verify", headers=owner, json={"token": token})
        assert expired.status_code == 410
