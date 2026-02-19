"""Session-based chat orchestrator for brief collection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from app.schemas import BriefSlots, ChatState, GateStatus, SlotUpdate


@dataclass
class ChatTurnResult:
    state: ChatState
    brief_slots: BriefSlots
    slot_updates: list[SlotUpdate]
    gate: GateStatus
    assistant_message: str


class ChatOrchestrator:
    """Collects brief slots through text turns and evaluates gate readiness."""

    REQUIRED_PATHS = (
        "product.name",
        "product.category",
        "product.features",
        "product.price_band",
        "target.who",
        "target.why",
        "channel.channels",
        "goal.weekly_goal",
    )

    CHANNEL_KEYWORDS = {
        "Instagram": ("인스타", "인스타그램", "instagram"),
        "YouTube Shorts": ("유튜브숏", "유튜브 쇼츠", "youtube shorts", "shorts"),
        "YouTube": ("유튜브", "youtube"),
        "Naver": ("네이버", "naver"),
        "SmartStore": ("스마트스토어", "smartstore", "스스"),
        "Coupang": ("쿠팡", "coupang"),
        "TikTok": ("틱톡", "tiktok"),
    }

    QUESTION_BY_PATH = {
        "product.name": "제품명(상품명)을 알려주세요.",
        "product.category": "제품 카테고리는 무엇인가요?",
        "product.features": "핵심 특징 3가지를 알려주세요. (쉼표로 구분)",
        "product.price_band": "가격대(저가/중가/프리미엄 또는 실제 가격)를 알려주세요.",
        "target.who": "주요 타겟 고객은 누구인가요?",
        "target.why": "그 타겟이 이 제품을 사는 이유는 무엇인가요?",
        "channel.channels": "우선 집중할 채널 1~2개를 알려주세요. (예: 인스타, 네이버)",
        "goal.weekly_goal": "이번 주 목표를 선택해주세요. (조회/문의/구매)",
    }
    SUPPORTED_VIDEO_SECONDS = (5, 10, 15, 20)

    @staticmethod
    def new_session_id() -> str:
        return f"sess_{uuid4().hex[:16]}"

    @staticmethod
    def empty_slots() -> BriefSlots:
        return BriefSlots()

    def process_turn(self, *, message: str, slots: BriefSlots) -> ChatTurnResult:
        normalized = message.strip()
        working_slots = slots.model_copy(deep=True)
        slot_updates, notices = self._extract_updates(message=normalized, slots=working_slots)

        for update in slot_updates:
            self._apply_update(slots=working_slots, update=update)

        gate = self.evaluate_gate(working_slots)
        if gate.ready:
            assistant_message = (
                "좋아요. 브리프 수집이 완료됐어요. "
                "이제 시장 리서치와 전략 생성을 진행할 수 있습니다."
            )
            state: ChatState = "BRIEF_READY"
        else:
            next_path = gate.missing_required[0]
            assistant_message = self.QUESTION_BY_PATH.get(
                next_path,
                "좋아요. 부족한 정보를 한 가지씩 채워볼게요.",
            )
            state = "CHAT_COLLECTING"

        if notices:
            assistant_message = "\n".join([*notices, assistant_message])

        return ChatTurnResult(
            state=state,
            brief_slots=working_slots,
            slot_updates=slot_updates,
            gate=gate,
            assistant_message=assistant_message,
        )

    def evaluate_gate(self, slots: BriefSlots) -> GateStatus:
        missing: list[str] = []
        for path in self.REQUIRED_PATHS:
            if path == "product.features":
                if len(slots.product.features) < 3:
                    missing.append(path)
                continue
            if path == "channel.channels":
                if not (1 <= len(slots.channel.channels) <= 2):
                    missing.append(path)
                continue

            value = self._get_path_value(slots=slots, path=path)
            if self._is_empty(value):
                missing.append(path)

        completeness = round((len(self.REQUIRED_PATHS) - len(missing)) / len(self.REQUIRED_PATHS), 3)
        return GateStatus(ready=not missing, missing_required=missing, completeness=completeness)

    def first_question(self) -> str:
        return self.QUESTION_BY_PATH["product.name"]

    def _extract_updates(self, *, message: str, slots: BriefSlots) -> tuple[list[SlotUpdate], list[str]]:
        updates: list[SlotUpdate] = []
        notices: list[str] = []
        lowered = message.lower()

        if not slots.product.name:
            name_match = re.search(
                r"(?:제품명|상품명|이름)\s*(?:은|는|:)?\s*([^\n,.;]{2,40})",
                message,
                flags=re.IGNORECASE,
            )
            if name_match:
                updates.append(
                    SlotUpdate(path="product.name", value=self._clean_fragment(name_match.group(1)), confidence=0.93)
                )

        if not slots.product.category:
            category_match = re.search(
                r"(?:카테고리|분야|업종)\s*(?:은|는|:)?\s*([^\n,.;]{2,40})",
                message,
                flags=re.IGNORECASE,
            )
            if category_match:
                updates.append(
                    SlotUpdate(
                        path="product.category",
                        value=self._clean_fragment(category_match.group(1)),
                        confidence=0.9,
                    )
                )
            else:
                inferred_category = self._infer_category(lowered)
                if inferred_category:
                    updates.append(
                        SlotUpdate(path="product.category", value=inferred_category, confidence=0.72)
                    )

        if len(slots.product.features) < 3:
            extracted_features = self._extract_features(message=message)
            if extracted_features:
                merged = self._merge_unique(slots.product.features, extracted_features, limit=6)
                if merged != slots.product.features:
                    updates.append(
                        SlotUpdate(path="product.features", value=merged, confidence=0.82)
                    )

        if not slots.product.price_band:
            price_band = self._extract_price_band(message=message, lowered=lowered)
            if price_band:
                updates.append(SlotUpdate(path="product.price_band", value=price_band, confidence=0.86))

        if not slots.target.who:
            who_match = re.search(
                r"(?:타겟|대상|고객)\s*(?:은|는|:)?\s*([^\n,.;]{2,60})",
                message,
                flags=re.IGNORECASE,
            )
            if who_match:
                updates.append(
                    SlotUpdate(path="target.who", value=self._clean_fragment(who_match.group(1)), confidence=0.88)
                )

        if not slots.target.why:
            why_match = re.search(
                r"(?:이유|니즈|문제|왜냐하면|왜)\s*(?:은|는|:)?\s*([^\n,.;]{2,80})",
                message,
                flags=re.IGNORECASE,
            )
            if why_match:
                updates.append(
                    SlotUpdate(path="target.why", value=self._clean_fragment(why_match.group(1)), confidence=0.84)
                )

        detected_channels = self._extract_channels(lowered=lowered)
        if detected_channels:
            merged_channels = self._merge_unique(slots.channel.channels, detected_channels, limit=2)
            if merged_channels != slots.channel.channels:
                updates.append(
                    SlotUpdate(path="channel.channels", value=merged_channels, confidence=0.9)
                )

        if not slots.goal.weekly_goal:
            goal = self._extract_goal(lowered=lowered)
            if goal:
                updates.append(SlotUpdate(path="goal.weekly_goal", value=goal, confidence=0.91))

        requested_video_seconds = self._extract_video_seconds(message=message, lowered=lowered)
        if requested_video_seconds is not None:
            current_video_seconds = slots.goal.video_seconds
            normalized_video_seconds = self._normalize_video_seconds(requested_video_seconds)
            if current_video_seconds != normalized_video_seconds:
                updates.append(
                    SlotUpdate(
                        path="goal.video_seconds",
                        value=normalized_video_seconds,
                        confidence=0.93,
                    )
                )
            if current_video_seconds != normalized_video_seconds or requested_video_seconds != normalized_video_seconds:
                notices.append(
                    self._build_video_seconds_notice(
                        requested=requested_video_seconds,
                        normalized=normalized_video_seconds,
                        previous=current_video_seconds,
                    )
                )

        return updates, notices

    @staticmethod
    def _extract_features(*, message: str) -> list[str]:
        if "특징" not in message and "장점" not in message and "핵심" not in message:
            return []

        candidate = message
        for token in ("특징", "장점", "핵심"):
            if token in candidate:
                candidate = candidate.split(token, maxsplit=1)[-1]
        parts = re.split(r"[,\n/|;·]+", candidate)
        cleaned = [ChatOrchestrator._clean_fragment(part) for part in parts]
        return [item for item in cleaned if len(item) >= 2]

    @staticmethod
    def _extract_price_band(*, message: str, lowered: str) -> str | None:
        if any(keyword in lowered for keyword in ("저가", "가성비", "저렴")):
            return "low"
        if any(keyword in lowered for keyword in ("중가", "중간 가격", "미드")):
            return "mid"
        if any(keyword in lowered for keyword in ("고가", "프리미엄", "고급")):
            return "premium"

        won_match = re.search(r"(\d[\d,]*)\s*원", message)
        if won_match:
            numeric = int(won_match.group(1).replace(",", ""))
            if numeric <= 30_000:
                return "low"
            if numeric <= 100_000:
                return "mid"
            return "premium"

        manwon_match = re.search(r"(\d+)\s*만\s*원", message)
        if manwon_match:
            numeric = int(manwon_match.group(1)) * 10_000
            if numeric <= 30_000:
                return "low"
            if numeric <= 100_000:
                return "mid"
            return "premium"

        return None

    def _extract_channels(self, *, lowered: str) -> list[str]:
        channels: list[str] = []
        for canonical, keywords in self.CHANNEL_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                channels.append(canonical)
        return channels[:2]

    @staticmethod
    def _extract_goal(*, lowered: str) -> str | None:
        if any(keyword in lowered for keyword in ("구매", "전환", "매출", "판매")):
            return "purchase"
        if any(keyword in lowered for keyword in ("문의", "리드", "상담")):
            return "inquiry"
        if any(keyword in lowered for keyword in ("조회", "도달", "노출", "리치")):
            return "reach"
        return None

    @staticmethod
    def _extract_video_seconds(*, message: str, lowered: str) -> int | None:
        explicit_patterns = (
            r"(?:영상|비디오|video)\s*(?:길이|시간|duration)?\s*(?:은|는|:)?\s*(\d{1,2})\s*초",
            r"(\d{1,2})\s*초(?:짜리)?\s*(?:영상|비디오|video|광고)",
        )
        for pattern in explicit_patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if match:
                return int(match.group(1))

        if any(keyword in lowered for keyword in ("영상", "비디오", "video", "광고", "숏폼")):
            fallback_match = re.search(r"(\d{1,2})\s*초", message)
            if fallback_match:
                return int(fallback_match.group(1))
        return None

    @classmethod
    def _normalize_video_seconds(cls, seconds: int) -> int:
        requested = max(1, int(seconds))
        return min(
            cls.SUPPORTED_VIDEO_SECONDS,
            key=lambda candidate: (abs(candidate - requested), candidate),
        )

    @classmethod
    def _build_video_seconds_notice(
        cls,
        *,
        requested: int,
        normalized: int,
        previous: int | None,
    ) -> str:
        supported = "/".join(str(value) for value in cls.SUPPORTED_VIDEO_SECONDS)
        if requested != normalized:
            return (
                f"영상 길이 {requested}초는 지원 범위를 벗어나 {normalized}초로 보정했어요. "
                f"(지원: {supported}초)"
            )
        if previous is None:
            return f"영상 길이를 {normalized}초로 설정했어요."
        return f"영상 길이를 {normalized}초로 변경했어요."

    @staticmethod
    def _infer_category(lowered: str) -> str | None:
        mapping = (
            (("스킨", "세럼", "화장품", "크림"), "스킨케어"),
            (("옷", "의류", "패션"), "패션"),
            (("건강식품", "영양제", "헬스"), "헬스케어"),
            (("식품", "간식", "음료"), "푸드"),
            (("가전", "디바이스", "기기"), "가전"),
        )
        for keywords, category in mapping:
            if any(keyword in lowered for keyword in keywords):
                return category
        return None

    @staticmethod
    def _merge_unique(existing: list[str], incoming: list[str], *, limit: int) -> list[str]:
        seen = {item.strip().lower() for item in existing if item.strip()}
        merged = [item for item in existing if item.strip()]
        for item in incoming:
            normalized = item.strip()
            key = normalized.lower()
            if not normalized or key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
            if len(merged) >= limit:
                break
        return merged

    @staticmethod
    def _clean_fragment(text: str) -> str:
        cleaned = text.strip().strip("\"'`")
        cleaned = re.sub(r"\s+", " ", cleaned)
        for suffix in ("입니다", "이에요", "예요", "입니다.", "이에요.", "예요."):
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)].strip()
        return cleaned

    @classmethod
    def _apply_update(cls, *, slots: BriefSlots, update: SlotUpdate) -> None:
        if update.path == "product.name":
            slots.product.name = str(update.value)
        elif update.path == "product.category":
            slots.product.category = str(update.value)
        elif update.path == "product.features":
            slots.product.features = [str(item) for item in update.value]
        elif update.path == "product.price_band":
            slots.product.price_band = str(update.value)
        elif update.path == "target.who":
            slots.target.who = str(update.value)
        elif update.path == "target.why":
            slots.target.why = str(update.value)
        elif update.path == "channel.channels":
            slots.channel.channels = [str(item) for item in update.value][:2]
        elif update.path == "goal.weekly_goal":
            normalized = str(update.value).strip().lower()
            if normalized in {"reach", "inquiry", "purchase"}:
                slots.goal.weekly_goal = normalized
        elif update.path == "goal.video_seconds":
            try:
                requested = int(update.value)
            except (TypeError, ValueError):
                return
            slots.goal.video_seconds = cls._normalize_video_seconds(requested)

    @staticmethod
    def _get_path_value(*, slots: BriefSlots, path: str) -> object:
        head, tail = path.split(".", maxsplit=1)
        bucket = getattr(slots, head)
        return getattr(bucket, tail)

    @staticmethod
    def _is_empty(value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, tuple, set)):
            return len(value) == 0
        return False
