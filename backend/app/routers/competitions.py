from datetime import datetime, timezone
from math import ceil, log2

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.tournament_models import Tournament, TournamentParticipant, TournamentMatch
from app.tournament_schemas import (
    MatchOutput, MatchScoreInput, ParticipantCreate, ParticipantOutput,
    TournamentCreate, TournamentOutput,
)

router = APIRouter(prefix="/competitions", tags=["competitions"])


def _is_admin(user: User) -> bool:
    return any(role.role == "admin" for role in user.roles)


def _can_manage(tournament: Tournament, user: User) -> bool:
    return tournament.organizer_id == user.id or _is_admin(user)


def _tournament_output(item: Tournament, db: Session) -> TournamentOutput:
    count = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == item.id,
        TournamentParticipant.status == "registered",
    ).count()
    return TournamentOutput(
        id=item.id, organizer_id=item.organizer_id, title=item.title, sport=item.sport,
        format=item.format, region=item.region, venue=item.venue, starts_at=item.starts_at,
        registration_deadline=item.registration_deadline, max_participants=item.max_participants,
        age_group=item.age_group, weight_class=item.weight_class, rules=item.rules,
        status=item.status, participant_count=count, created_at=item.created_at,
    )


def _participant_output(item: TournamentParticipant) -> ParticipantOutput:
    return ParticipantOutput(
        id=item.id, tournament_id=item.tournament_id,
        full_name=item.full_name, club_name=item.club_name,
        seed=item.seed, status=item.status, created_at=item.created_at,
    )


def _match_output(item: TournamentMatch, db: Session) -> MatchOutput:
    first = db.get(TournamentParticipant, item.participant1_id) if item.participant1_id else None
    second = db.get(TournamentParticipant, item.participant2_id) if item.participant2_id else None
    return MatchOutput(
        id=item.id, tournament_id=item.tournament_id, round_number=item.round_number,
        match_number=item.match_number, stage_name=item.stage_name,
        participant1_id=item.participant1_id, participant1_name=first.full_name if first else None,
        participant2_id=item.participant2_id, participant2_name=second.full_name if second else None,
        winner_id=item.winner_id, score1=item.score1, score2=item.score2, status=item.status,
        scheduled_at=item.scheduled_at, mat_name=item.mat_name, next_match_id=item.next_match_id,
    )


def _get_tournament_or_404(db: Session, tournament_id: int) -> Tournament:
    item = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Тэмцээн олдсонгүй.")
    return item


def _advance_winner(db: Session, match: TournamentMatch) -> None:
    if match.next_match_id is None or match.winner_id is None:
        return
    next_match = db.query(TournamentMatch).filter(TournamentMatch.id == match.next_match_id).first()
    if next_match is None:
        return
    if match.next_slot == "p1":
        next_match.participant1_id = match.winner_id
    elif match.next_slot == "p2":
        next_match.participant2_id = match.winner_id
    if next_match.participant1_id is not None and next_match.participant2_id is not None:
        next_match.status = "scheduled"


def _stage_name(round_number: int, total_rounds: int) -> str:
    remaining = total_rounds - round_number + 1
    labels = {1: "Финал", 2: "Хагас шигшээ", 3: "Шөвгийн 8", 4: "Шөвгийн 16"}
    return labels.get(remaining, f"{round_number}-р тойрог")


def _seeded_bracket_slots(participants: list[TournamentParticipant], bracket_size: int):
    # Standard seeded placement: 1 vs lowest seed, 2 vs next-lowest, etc.
    positions = [1, 2]
    while len(positions) < bracket_size:
        next_size = len(positions) * 2
        positions = [
            seed
            for position in positions
            for seed in (position, next_size + 1 - position)
        ]
    return [
        participants[seed - 1] if seed <= len(participants) else None
        for seed in positions
    ]


@router.get("", response_model=list[TournamentOutput])
def list_competitions(
    sport: str | None = Query(default=None, max_length=80),
    region: str | None = Query(default=None, max_length=120),
    search: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None, pattern="^(registration_open|registration_closed|in_progress|completed|cancelled)$"),
    db: Session = Depends(get_db),
):
    query = db.query(Tournament)
    if sport:
        query = query.filter(Tournament.sport.ilike(f"%{sport.strip()}%"))
    if region:
        query = query.filter(Tournament.region.ilike(f"%{region.strip()}%"))
    if search:
        query = query.filter(Tournament.title.ilike(f"%{search.strip()}%"))
    if status:
        query = query.filter(Tournament.status == status)
    else:
        query = query.filter(Tournament.status.in_(["registration_open", "registration_closed", "in_progress", "completed"]))
    rows = query.order_by(Tournament.starts_at.asc()).limit(200).all()
    return [_tournament_output(item, db) for item in rows]


@router.post("", response_model=TournamentOutput, status_code=201)
def create_competition(
    payload: TournamentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    starts_at = payload.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    if starts_at <= now:
        raise HTTPException(status_code=400, detail="Тэмцээний эхлэх цаг ирээдүйд байх ёстой.")
    deadline = payload.registration_deadline
    if deadline is not None:
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline >= starts_at:
            raise HTTPException(status_code=400, detail="Бүртгэлийн эцсийн хугацаа тэмцээнээс өмнө байна.")
    item = Tournament(
        organizer_id=user.id, title=payload.title, sport=payload.sport, format=payload.format,
        region=payload.region, venue=payload.venue, starts_at=starts_at,
        registration_deadline=deadline, max_participants=payload.max_participants,
        age_group=payload.age_group, weight_class=payload.weight_class, rules=payload.rules,
        status="registration_open",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _tournament_output(item, db)


@router.get("/mine", response_model=list[TournamentOutput])
def list_my_competitions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Tournament).filter(Tournament.organizer_id == user.id).order_by(Tournament.created_at.desc()).limit(100).all()
    return [_tournament_output(item, db) for item in rows]


@router.get("/{tournament_id}", response_model=TournamentOutput)
def get_competition(tournament_id: int, db: Session = Depends(get_db)):
    return _tournament_output(_get_tournament_or_404(db, tournament_id), db)


@router.post("/{tournament_id}/register", response_model=ParticipantOutput, status_code=201)
def register_participant(
    tournament_id: int,
    payload: ParticipantCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).with_for_update().first()
    if tournament is None:
        raise HTTPException(status_code=404, detail="Тэмцээн олдсонгүй.")
    if tournament.status != "registration_open":
        raise HTTPException(status_code=409, detail="Энэ тэмцээний бүртгэл хаагдсан байна.")
    now = datetime.now(timezone.utc)
    deadline = tournament.registration_deadline
    if deadline is not None:
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= now:
            raise HTTPException(status_code=409, detail="Бүртгэлийн хугацаа дууссан байна.")
    count = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id,
        TournamentParticipant.status == "registered",
    ).count()
    if count >= tournament.max_participants:
        raise HTTPException(status_code=409, detail="Тэмцээний оролцогчийн дээд тоо дүүрсэн байна.")
    existing = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id,
        TournamentParticipant.contact_phone == payload.contact_phone,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Энэ утасны дугаараар оролцогч бүртгэгдсэн байна.")
    if payload.seed > 0:
        seed_exists = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament.id,
            TournamentParticipant.seed == payload.seed,
        ).first()
        if seed_exists:
            raise HTTPException(status_code=409, detail="Энэ суулгалтын эрэмбэ өөр тамирчинд олгогдсон байна.")
    item = TournamentParticipant(
        tournament_id=tournament.id, user_id=user.id, full_name=payload.full_name,
        club_name=payload.club_name, contact_phone=payload.contact_phone, seed=payload.seed,
        status="registered",
    )
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Оролцогчийн бүртгэл давхардсан байна.")
    return _participant_output(item)


@router.get("/{tournament_id}/participants", response_model=list[ParticipantOutput])
def list_participants(tournament_id: int, db: Session = Depends(get_db)):
    tournament = _get_tournament_or_404(db, tournament_id)
    rows = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id,
        TournamentParticipant.status == "registered",
    ).order_by(TournamentParticipant.seed.desc(), TournamentParticipant.created_at.asc()).all()
    return [_participant_output(item) for item in rows]


@router.post("/{tournament_id}/close-registration", response_model=TournamentOutput)
def close_registration(
    tournament_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tournament = _get_tournament_or_404(db, tournament_id)
    if not _can_manage(tournament, user):
        raise HTTPException(status_code=403, detail="Зөвхөн зохион байгуулагч бүртгэл хаана.")
    if tournament.status != "registration_open":
        raise HTTPException(status_code=409, detail="Бүртгэлийг хаах боломжгүй төлөвтэй байна.")
    tournament.status = "registration_closed"
    db.commit()
    db.refresh(tournament)
    return _tournament_output(tournament, db)


@router.post("/{tournament_id}/draw", response_model=list[MatchOutput], status_code=201)
def generate_draw(
    tournament_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tournament = _get_tournament_or_404(db, tournament_id)
    if not _can_manage(tournament, user):
        raise HTTPException(status_code=403, detail="Зөвхөн зохион байгуулагч сугалаа үүсгэнэ.")
    existing = db.query(TournamentMatch).filter(TournamentMatch.tournament_id == tournament.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Сугалаа өмнө нь үүссэн байна.")
    participants = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id,
        TournamentParticipant.status == "registered",
    ).all()
    participants.sort(key=lambda p: (p.seed == 0, p.seed if p.seed else p.id))
    if len(participants) < 2:
        raise HTTPException(status_code=400, detail="Сугалаа үүсгэхэд дор хаяж 2 оролцогч шаардлагатай.")

    rounds: list[list[TournamentMatch]] = []
    if tournament.format == "round_robin":
        pool = list(participants)
        if len(pool) % 2:
            pool.append(None)
        count = len(pool)
        total_rounds = count - 1
        for round_index in range(total_rounds):
            round_matches = []
            for pair_index in range(count // 2):
                first = pool[pair_index]
                second = pool[count - pair_index - 1]
                if first is not None and second is not None:
                    match = TournamentMatch(
                        tournament_id=tournament.id, round_number=round_index + 1,
                        match_number=len(round_matches) + 1, stage_name=f"{round_index + 1}-р тойрог",
                        participant1_id=first.id, participant2_id=second.id, status="scheduled",
                    )
                    db.add(match)
                    round_matches.append(match)
            rounds.append(round_matches)
            pool = [pool[0], pool[-1], *pool[1:-1]]
    else:
        total_rounds = ceil(log2(len(participants)))
        bracket_size = 2 ** total_rounds
        first_round_count = bracket_size // 2
        for round_index in range(total_rounds):
            match_count = first_round_count // (2 ** round_index)
            round_matches = []
            for match_index in range(match_count):
                match = TournamentMatch(
                    tournament_id=tournament.id,
                    round_number=round_index + 1,
                    match_number=match_index + 1,
                    stage_name=_stage_name(round_index + 1, total_rounds),
                    status="waiting",
                )
                db.add(match)
                round_matches.append(match)
            rounds.append(round_matches)
        db.flush()
        bracket_slots = _seeded_bracket_slots(participants, bracket_size)
        for index, match in enumerate(rounds[0]):
            first_index = index * 2
            first = bracket_slots[first_index]
            second = bracket_slots[first_index + 1]
            match.participant1_id = first.id if first else None
            match.participant2_id = second.id if second else None
            if first is not None and second is None:
                match.status = "completed"
                match.winner_id = first.id
            elif first is not None and second is not None:
                match.status = "scheduled"
        for round_index in range(len(rounds) - 1):
            for match_index, match in enumerate(rounds[round_index]):
                match.next_match_id = rounds[round_index + 1][match_index // 2].id
                match.next_slot = "p1" if match_index % 2 == 0 else "p2"
        for match in rounds[0]:
            if match.status == "completed":
                _advance_winner(db, match)
    db.flush()
    tournament.status = "in_progress"
    db.commit()
    matches = db.query(TournamentMatch).filter(
        TournamentMatch.tournament_id == tournament.id
    ).order_by(TournamentMatch.round_number, TournamentMatch.match_number).all()
    return [_match_output(item, db) for item in matches]


@router.get("/{tournament_id}/matches", response_model=list[MatchOutput])
def list_matches(tournament_id: int, db: Session = Depends(get_db)):
    tournament = _get_tournament_or_404(db, tournament_id)
    rows = db.query(TournamentMatch).filter(
        TournamentMatch.tournament_id == tournament.id
    ).order_by(TournamentMatch.round_number, TournamentMatch.match_number).all()
    return [_match_output(item, db) for item in rows]


@router.post("/{tournament_id}/matches/{match_id}/score", response_model=MatchOutput)
def update_match_score(
    tournament_id: int,
    match_id: int,
    payload: MatchScoreInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tournament = _get_tournament_or_404(db, tournament_id)
    if not _can_manage(tournament, user):
        raise HTTPException(status_code=403, detail="Зөвхөн зохион байгуулагч оноо бүртгэнэ.")
    match = db.query(TournamentMatch).filter(
        TournamentMatch.id == match_id,
        TournamentMatch.tournament_id == tournament.id,
    ).first()
    if match is None:
        raise HTTPException(status_code=404, detail="Тоглолт олдсонгүй.")
    if match.status != "scheduled":
        raise HTTPException(status_code=409, detail="Энэ тоглолтын оноо бүртгэхэд бэлэн биш байна.")
    if match.participant1_id is None or match.participant2_id is None:
        raise HTTPException(status_code=409, detail="Тоглолтын хоёр оролцогч бүрдээгүй байна.")
    if tournament.format == "single_elimination" and payload.score1 == payload.score2:
        raise HTTPException(status_code=400, detail="Хасагдах шатанд тэнцээ байж болохгүй.")
    match.score1 = payload.score1
    match.score2 = payload.score2
    match.scheduled_at = payload.scheduled_at
    match.mat_name = payload.mat_name
    if payload.score1 > payload.score2:
        match.winner_id = match.participant1_id
    elif payload.score2 > payload.score1:
        match.winner_id = match.participant2_id
    else:
        match.winner_id = None
    match.status = "completed"
    _advance_winner(db, match)
    db.flush()
    all_matches = db.query(TournamentMatch).filter(TournamentMatch.tournament_id == tournament.id).all()
    if all(item.status == "completed" for item in all_matches):
        tournament.status = "completed"
    else:
        tournament.status = "in_progress"
    db.commit()
    db.refresh(match)
    return _match_output(match, db)
