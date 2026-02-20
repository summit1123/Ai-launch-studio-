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
        "product.price_band",
        "target.who",
        "channel.channels",
        "goal.weekly_goal",
        "product.features",
        "target.why",
    )
    ESSENTIAL_PATHS = (
        "product.name",
        "product.category",
        "target.who",
        "goal.weekly_goal",
    )
    RELAXED_READY_MIN_COMPLETENESS = 0.625

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
        "product.name": "홍보할 제품명(상품명)을 정확히 알려주세요.",
        "product.category": "제품 카테고리는 무엇인가요? 시장/경쟁 분석 기준으로 사용됩니다.",
        "product.features": "핵심 특징 3가지를 알려주세요. (쉼표로 구분, 예: 저자극, 빠른 흡수, 비건 포뮬러)",
        "product.price_band": "가격대(저가/중가/프리미엄 또는 실제 가격)를 알려주세요. 예: 39,000원",
        "target.who": "주요 타겟 고객은 누구인가요? 연령/상황을 포함해 1문장으로 적어주세요.",
        "target.why": "그 타겟이 이 제품을 사는 이유를 1문장으로 알려주세요.",
        "channel.channels": "우선 집중할 채널 1~2개를 알려주세요. 예: 인스타, 네이버",
        "goal.weekly_goal": "이번 주 목표를 선택해주세요. (조회/문의/구매 중 1개)",
    }
    SLOT_LABEL_BY_PATH = {
        "product.name": "제품명",
        "product.category": "카테고리",
        "product.features": "핵심 특징",
        "product.price_band": "가격대",
        "product.image_url": "제품 이미지",
        "product.image_context": "이미지 요약",
        "target.who": "타겟 고객",
        "target.why": "구매 이유",
        "channel.channels": "집중 채널",
        "goal.weekly_goal": "주간 목표",
        "goal.video_seconds": "영상 길이",
    }
    HINT_BY_PATH = {
        "product.name": "예: 아이폰 17, 글로우세럼X",
        "product.category": "예: 스마트폰, 스킨케어",
        "product.features": "예: 저자극, 빠른 흡수, 비건 포뮬러",
        "product.price_band": "예: 중가 또는 39,000원",
        "target.who": "예: 20대 직장인, 30대 남성",
        "target.why": "예: 촉촉함 유지, 트러블 진정",
        "channel.channels": "예: 인스타, 네이버",
        "goal.weekly_goal": "예: 문의",
    }
    BRIDGE_BY_PATH = {
        "product.name": "먼저 제품 식별부터 맞출게요.",
        "product.category": "시장 맥락을 정확히 잡기 위해",
        "product.features": "메시지/소재 품질을 올리려면",
        "product.price_band": "포지셔닝을 흔들리지 않게 하려면",
        "target.who": "누가 사는지 선명해야 전략이 살아나요.",
        "target.why": "구매 트리거를 알아야 카피가 맞아떨어져요.",
        "channel.channels": "실행 채널을 좁히면 속도가 올라갑니다.",
        "goal.weekly_goal": "이번 주 판단 기준을 고정하려면",
    }
    GOAL_LABELS = {
        "reach": "조회",
        "inquiry": "문의",
        "purchase": "구매",
    }
    FIELD_REASON_BY_PATH = {
        "product.name": "제품명을 알아야 시장/경쟁 데이터를 정확히 붙일 수 있어요.",
        "product.category": "카테고리가 있어야 비교 기준과 벤치마크가 맞아집니다.",
        "product.features": "핵심 특징이 있어야 카피와 영상 훅을 정확히 만들 수 있어요.",
        "product.price_band": "가격대를 알아야 메시지 톤과 혜택 포인트를 맞출 수 있어요.",
        "target.who": "타겟이 선명해야 반응할 문구와 채널 우선순위가 정해져요.",
        "target.why": "구매 이유를 알아야 전환형 문장을 만들 수 있어요.",
        "channel.channels": "채널이 정해져야 실행 형식(카피/영상 길이/포맷)을 맞출 수 있어요.",
        "goal.weekly_goal": "목표가 있어야 KPI와 실행 우선순위를 고를 수 있어요.",
    }
    FEATURE_FALLBACK_STOPWORDS = {
        "그리고",
        "또한",
        "및",
        "특징",
        "장점",
        "핵심",
        "제품",
        "카테고리",
        "타겟",
        "목표",
        "채널",
        "알려줘",
        "알려주세요",
        "알려주세요.",
        "주세요",
        "해주세요",
        "입니다",
        "이에요",
        "예요",
    }
    LOW_PRICE_CUE_KEYWORDS = (
        "초특가",
        "특가",
        "세일",
        "할인",
        "저렴",
        "가성비",
        "핫딜",
        "최저가",
    )
    DELEGATE_KEYWORDS = (
        "알아서",
        "니가",
        "네가",
        "추천",
        "골라",
        "정해",
        "맡길게",
        "맡긴다",
        "아무거나",
    )
    SUPPORTED_VIDEO_SECONDS = (4, 8, 12)
    EXTERNAL_UPDATE_ALLOWED_PATHS = frozenset(
        {
            "product.name",
            "product.category",
            "product.features",
            "product.price_band",
            "target.who",
            "target.why",
            "channel.channels",
            "goal.weekly_goal",
            "goal.video_seconds",
        }
    )

    @staticmethod
    def new_session_id() -> str:
        return f"sess_{uuid4().hex[:16]}"

    @staticmethod
    def empty_slots() -> BriefSlots:
        return BriefSlots()

    def process_turn(
        self,
        *,
        message: str,
        slots: BriefSlots,
        external_updates: list[SlotUpdate] | None = None,
    ) -> ChatTurnResult:
        normalized = message.strip()
        working_slots = slots.model_copy(deep=True)

        prepared_external_updates = self.prepare_external_updates(
            updates=external_updates or [],
            slots=working_slots,
            user_message=normalized,
        )
        for update in prepared_external_updates:
            self._apply_update(slots=working_slots, update=update)

        rule_updates, notices = self._extract_updates(message=normalized, slots=working_slots)

        for update in rule_updates:
            self._apply_update(slots=working_slots, update=update)

        slot_updates = self._dedupe_updates([*prepared_external_updates, *rule_updates])
        gate = self.evaluate_gate(working_slots)
        state, assistant_message = self._next_state_and_message(
            gate=gate,
            slot_updates=slot_updates,
            slots=working_slots,
            user_message=normalized,
        )

        if notices:
            assistant_message = "\n".join([*notices, assistant_message])

        return ChatTurnResult(
            state=state,
            brief_slots=working_slots,
            slot_updates=slot_updates,
            gate=gate,
            assistant_message=assistant_message,
        )

    def prepare_external_updates(
        self,
        *,
        updates: list[SlotUpdate],
        slots: BriefSlots,
        user_message: str = "",
    ) -> list[SlotUpdate]:
        if not updates:
            return []

        working_slots = slots.model_copy(deep=True)
        accepted: list[SlotUpdate] = []
        for update in updates:
            normalized = self._normalize_external_update(
                update=update,
                slots=working_slots,
                user_message=user_message,
            )
            if normalized is None:
                continue
            if any(
                existing.path == normalized.path and existing.value == normalized.value
                for existing in accepted
            ):
                continue
            self._apply_update(slots=working_slots, update=normalized)
            accepted.append(normalized)
        return accepted

    def _compose_ready_message(self, slot_updates: list[SlotUpdate]) -> str:
        summary = self._summarize_updates(slot_updates)
        if summary:
            return (
                f"{summary}까지 반영됐어요. "
                "이제 기획 보고서를 생성해서 시장 분석과 실행안을 바로 만들 수 있어요."
            )
        return (
            "필수 정보가 모두 채워졌어요. "
            "이제 기획 보고서를 생성해서 시장 분석과 실행안을 진행할 수 있어요."
        )

    def _compose_followup_message(
        self,
        *,
        slot_updates: list[SlotUpdate],
        next_path: str,
        slots: BriefSlots,
        user_message: str = "",
    ) -> str:
        question = self.QUESTION_BY_PATH.get(
            next_path,
            "다음 정보 한 가지만 더 알려주세요.",
        )
        summary = self._summarize_updates(slot_updates)
        path_specific = self._compose_path_specific_prompt(
            next_path=next_path,
            slots=slots,
            has_updates=bool(slot_updates),
            user_message=user_message,
        )
        bridge = self.BRIDGE_BY_PATH.get(next_path, "다음 단계로 넘어가려면")
        if summary:
            if path_specific:
                return f"{summary} 반영했어요. {path_specific}"
            return f"{summary} 반영했어요. {bridge} {question}"

        if path_specific:
            return path_specific
        hint = self.HINT_BY_PATH.get(next_path)
        if hint:
            return f"{bridge} {question} ({hint})"
        return question

    def _compose_path_specific_prompt(
        self,
        *,
        next_path: str,
        slots: BriefSlots,
        has_updates: bool,
        user_message: str,
    ) -> str | None:
        if user_message and not has_updates and self._looks_like_user_question(user_message):
            question_first = self._compose_question_first_reply(
                next_path=next_path,
                slots=slots,
                user_message=user_message,
            )
            if question_first:
                return question_first
            reason = self.FIELD_REASON_BY_PATH.get(next_path)
            question = self.QUESTION_BY_PATH.get(next_path, "다음 정보 한 가지만 더 알려주세요.")
            if reason:
                return f"좋은 질문이에요. {reason} {question}"
            return f"좋은 질문이에요. {question}"

        if next_path == "product.features":
            feature_count = len(slots.product.features)
            remaining = max(0, 3 - feature_count)
            if feature_count >= 3:
                return None
            if feature_count > 0:
                return (
                    f"핵심 특징은 {feature_count}개까지 정리됐어요. "
                    f"홍보 문구 완성도를 위해 {remaining}개만 더 알려주세요."
                )
            if user_message and not has_updates:
                return (
                    "입력해준 내용을 읽었는데 특징이 분리되지 않았어요. "
                    "쉼표로 구분해서 3개만 알려주세요. 예: 저자극, 빠른 흡수, 비건 포뮬러"
                )
            return None

        if next_path == "channel.channels":
            channel_count = len(slots.channel.channels)
            if channel_count == 1:
                return (
                    f"채널은 {slots.channel.channels[0]}로 반영했어요. "
                    "한 채널 더 추가할지, 이 채널 하나로 갈지 정해주세요."
                )
            if user_message and not has_updates:
                return "채널명을 정확히 인식하지 못했어요. 인스타/유튜브/네이버처럼 1~2개만 적어주세요."
            return None

        if next_path == "goal.weekly_goal":
            if slots.goal.weekly_goal:
                goal_label = self.GOAL_LABELS.get(slots.goal.weekly_goal, slots.goal.weekly_goal)
                return f"이번 주 목표는 {goal_label}로 잡혔어요."
            if user_message and not has_updates:
                return "이번 주 목표를 조회/문의/구매 중 하나로만 정해주세요."
            return None

        if next_path == "product.price_band" and user_message and not has_updates:
            inferred_price_band = self._extract_price_band(
                message=user_message,
                lowered=user_message.lower(),
                allow_plain_number=True,
            )
            if inferred_price_band and self._has_discount_premium_conflict(
                message=user_message,
                lowered=user_message.lower(),
                price_band=inferred_price_band,
            ):
                numeric = self._extract_price_numeric_krw(user_message)
                if numeric is not None:
                    return (
                        f"할인/초특가 표현과 {numeric:,}원 금액이 함께 보여서 확인이 필요해요. "
                        "금액이 맞나요, 아니면 15,000원처럼 다른 가격을 뜻한 걸까요?"
                    )
                return "할인/초특가 표현과 금액 정보가 함께 보여서 가격을 다시 확인할게요. 대표 판매가를 숫자로 알려주세요."
            return "가격대는 저가/중가/프리미엄 중 하나나 실제 가격(예: 39,000원)으로 알려주세요."

        if next_path == "target.why" and user_message and not has_updates:
            return "좋아요. 타겟이 구매하는 가장 큰 이유를 한 문장으로만 알려주세요."

        return None

    def _compose_question_first_reply(
        self,
        *,
        next_path: str,
        slots: BriefSlots,
        user_message: str,
    ) -> str | None:
        lowered = user_message.lower()
        question = self.QUESTION_BY_PATH.get(next_path, "다음 정보 한 가지만 더 알려주세요.")
        reason = self.FIELD_REASON_BY_PATH.get(next_path)

        if any(token in lowered for token in ("숫자만", "원 없이", "숫자로", "숫자")) and any(
            token in lowered for token in ("가격", "금액", "원")
        ):
            return (
                "가격은 숫자만 입력해도 인식돼요. "
                "예를 들면 39000 또는 39,000원처럼 보내주시면 됩니다. "
                f"{question}"
            )

        if any(token in lowered for token in ("뭐가 필요", "무엇이 필요", "뭐 더", "뭘 더", "남았", "다음엔")):
            missing_labels = self._missing_labels(slots=slots, limit=3)
            if missing_labels:
                joined = ", ".join(missing_labels)
                return f"지금은 {joined} 정보가 남아 있어요. 우선 {question}"
            return f"핵심 정보는 거의 다 채워졌어요. {question}"

        if any(token in lowered for token in ("왜", "필요", "이유", "말이 돼", "맞아", "맞나요")):
            if reason:
                return f"{reason} 그래서 지금은 {question}"
            return f"지금 단계에서는 해당 정보를 먼저 맞춰야 해요. {question}"

        return None

    def _summarize_updates(self, updates: list[SlotUpdate]) -> str:
        if not updates:
            return ""

        chunks: list[str] = []
        for update in updates:
            label = self.SLOT_LABEL_BY_PATH.get(update.path)
            if not label:
                continue
            value = self._format_update_value(update.value)
            if not value:
                continue
            chunks.append(f"{label} '{value}'")
            if len(chunks) >= 2:
                break
        return ", ".join(chunks)

    @staticmethod
    def _format_update_value(value: object) -> str:
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return ", ".join(items[:3])
        return str(value).strip()

    def _missing_labels(self, *, slots: BriefSlots, limit: int = 3) -> list[str]:
        gate = self.evaluate_gate(slots)
        labels: list[str] = []
        for path in gate.missing_required:
            label = self.SLOT_LABEL_BY_PATH.get(path)
            if not label:
                continue
            labels.append(label)
            if len(labels) >= limit:
                break
        return labels

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
        strict_ready = not missing
        essential_ready = self._is_paths_satisfied(slots=slots, paths=self.ESSENTIAL_PATHS)
        relaxed_ready = (
            essential_ready
            and completeness >= self.RELAXED_READY_MIN_COMPLETENESS
        )
        return GateStatus(
            ready=strict_ready or relaxed_ready,
            missing_required=missing,
            completeness=completeness,
        )

    def first_question(self) -> str:
        return (
            "홍보 기획을 같이 정리해볼게요. "
            f"우선 {self.QUESTION_BY_PATH['product.name']} "
            "제품 이미지가 있으면 먼저 올려도 됩니다."
        )

    def compose_message_from_updates(
        self,
        *,
        slot_updates: list[SlotUpdate],
        gate: GateStatus,
        slots: BriefSlots,
    ) -> str:
        _, message = self._next_state_and_message(
            gate=gate,
            slot_updates=slot_updates,
            slots=slots,
        )
        return message

    def apply_image_analysis(
        self,
        *,
        slots: BriefSlots,
        image_url: str,
        image_summary: str | None,
        inferred_category: str | None,
        inferred_features: list[str],
    ) -> list[SlotUpdate]:
        updates: list[SlotUpdate] = []

        if image_url and slots.product.image_url != image_url:
            updates.append(SlotUpdate(path="product.image_url", value=image_url, confidence=1.0))
            slots.product.image_url = image_url
        if image_summary and slots.product.image_context != image_summary:
            updates.append(SlotUpdate(path="product.image_context", value=image_summary, confidence=0.76))
            slots.product.image_context = image_summary
        if inferred_category and not slots.product.category:
            updates.append(SlotUpdate(path="product.category", value=inferred_category, confidence=0.66))
            slots.product.category = inferred_category
        if inferred_features:
            merged_features = self._merge_unique(slots.product.features, inferred_features, limit=6)
            if merged_features != slots.product.features:
                updates.append(
                    SlotUpdate(path="product.features", value=merged_features, confidence=0.68)
                )
                slots.product.features = merged_features

        return updates

    def _next_state_and_message(
        self,
        *,
        gate: GateStatus,
        slot_updates: list[SlotUpdate],
        slots: BriefSlots,
        user_message: str = "",
    ) -> tuple[ChatState, str]:
        if gate.ready:
            if gate.missing_required:
                return (
                    "BRIEF_READY",
                    "핵심 정보가 충분히 모였어요. 먼저 기획 보고서를 생성하고, "
                    "부족한 정보는 결과를 보면서 보완해도 됩니다.",
                )
            return "BRIEF_READY", self._compose_ready_message(slot_updates)
        return "CHAT_COLLECTING", self._compose_followup_message(
            slot_updates=slot_updates,
            next_path=gate.missing_required[0],
            slots=slots,
            user_message=user_message,
        )

    def _extract_updates(self, *, message: str, slots: BriefSlots) -> tuple[list[SlotUpdate], list[str]]:
        updates: list[SlotUpdate] = []
        notices: list[str] = []
        lowered = message.lower()
        expected_path = self._first_missing_path(slots)

        if not slots.product.name:
            name_match = re.search(
                r"(?:제품명|상품명|이름)\s*(?:은|는|:)?\s*([^\n,.;]{2,40})",
                message,
                flags=re.IGNORECASE,
            )
            if name_match:
                name_candidate = self._clean_fragment(name_match.group(1))
                if self._looks_like_user_question(name_candidate):
                    name_candidate = ""
            else:
                name_candidate = ""
            if name_candidate:
                updates.append(
                    SlotUpdate(path="product.name", value=name_candidate, confidence=0.93)
                )

        if not slots.product.category:
            category_match = re.search(
                r"(?:카테고리|분야|업종)\s*(?:은|는|:)?\s*([^\n,.;]{2,40})",
                message,
                flags=re.IGNORECASE,
            )
            if category_match:
                category_candidate = self._clean_fragment(category_match.group(1))
                if self._looks_like_user_question(category_candidate):
                    category_candidate = ""
            else:
                category_candidate = ""
            if category_candidate:
                updates.append(
                    SlotUpdate(
                        path="product.category",
                        value=category_candidate,
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
            if not extracted_features and expected_path == "product.features":
                extracted_features = self._extract_features(
                    message=message,
                    require_keyword=False,
                )
            if extracted_features:
                merged = self._merge_unique(slots.product.features, extracted_features, limit=6)
                if merged != slots.product.features:
                    updates.append(
                        SlotUpdate(path="product.features", value=merged, confidence=0.82)
                    )

        if not slots.product.price_band:
            price_band = self._extract_price_band(
                message=message,
                lowered=lowered,
                allow_plain_number=expected_path == "product.price_band",
            )
            if price_band and not self._has_discount_premium_conflict(
                message=message,
                lowered=lowered,
                price_band=price_band,
            ):
                updates.append(SlotUpdate(path="product.price_band", value=price_band, confidence=0.86))

        if not slots.target.who:
            who_match = re.search(
                r"(?:타겟|대상|고객)\s*(?:은|는|:)?\s*([^\n,.;]{2,60})",
                message,
                flags=re.IGNORECASE,
            )
            if who_match:
                who_candidate = self._clean_fragment(who_match.group(1))
                if self._looks_like_user_question(who_candidate):
                    who_candidate = ""
            else:
                who_candidate = ""
            if who_candidate:
                updates.append(
                    SlotUpdate(path="target.who", value=who_candidate, confidence=0.88)
                )

        if not slots.target.why:
            why_match = re.search(
                r"(?:이유|니즈|문제|왜냐하면|왜)\s*(?:은|는|:)?\s*([^\n,.;]{2,80})",
                message,
                flags=re.IGNORECASE,
            )
            if why_match:
                why_candidate = self._clean_fragment(why_match.group(1))
                if self._looks_like_user_question(why_candidate):
                    why_candidate = ""
            else:
                why_candidate = ""
            if why_candidate:
                updates.append(
                    SlotUpdate(path="target.why", value=why_candidate, confidence=0.84)
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

        if expected_path and expected_path not in {update.path for update in updates}:
            fallback_update = self._infer_update_for_expected_path(
                message=message,
                lowered=lowered,
                expected_path=expected_path,
                slots=slots,
            )
            if fallback_update is not None:
                updates.append(fallback_update)

        return updates, notices

    def _normalize_external_update(
        self,
        *,
        update: SlotUpdate,
        slots: BriefSlots,
        user_message: str = "",
    ) -> SlotUpdate | None:
        path = str(update.path).strip()
        if path not in self.EXTERNAL_UPDATE_ALLOWED_PATHS:
            return None

        confidence = max(0.0, min(1.0, float(update.confidence)))
        value = update.value

        if path == "product.features":
            incoming = self._coerce_string_list(value)
            filtered = self._filter_feature_terms(incoming)
            if not filtered:
                return None
            merged = self._merge_unique(slots.product.features, filtered, limit=6)
            if merged == slots.product.features:
                return None
            return SlotUpdate(path=path, value=merged, confidence=confidence)

        if path == "channel.channels":
            channels = self._normalize_channel_list(value)
            if not channels:
                return None
            merged = self._merge_unique(slots.channel.channels, channels, limit=2)
            if merged == slots.channel.channels:
                return None
            return SlotUpdate(path=path, value=merged, confidence=confidence)

        if path == "product.price_band":
            if slots.product.price_band:
                return None
            normalized_price = self._normalize_price_band_value(value)
            if not normalized_price:
                return None
            if self._has_discount_premium_conflict(
                message=user_message,
                lowered=user_message.lower(),
                price_band=normalized_price,
            ):
                return None
            return SlotUpdate(path=path, value=normalized_price, confidence=confidence)

        if path == "goal.weekly_goal":
            if slots.goal.weekly_goal:
                return None
            normalized_goal = self._normalize_goal_value(value)
            if not normalized_goal:
                return None
            return SlotUpdate(path=path, value=normalized_goal, confidence=confidence)

        if path == "goal.video_seconds":
            try:
                requested = int(value)
            except (TypeError, ValueError):
                return None
            return SlotUpdate(
                path=path,
                value=self._normalize_video_seconds(requested),
                confidence=confidence,
            )

        cleaned = self._clean_fragment(str(value))
        if len(cleaned) < 2:
            return None

        # 외부 추출은 기존 값을 덮어쓰기보다 빈 슬롯 채우기 용도로만 사용한다.
        if path == "product.name" and slots.product.name:
            return None
        if path == "product.category" and slots.product.category:
            return None
        if path == "target.who" and slots.target.who:
            return None
        if path == "target.why" and slots.target.why:
            return None

        return SlotUpdate(path=path, value=cleaned, confidence=confidence)

    @classmethod
    def _coerce_string_list(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [cls._clean_fragment(str(item)) for item in value if cls._clean_fragment(str(item))]
        if isinstance(value, str):
            parts = re.split(r"[,/\n|;·]+", value)
            return [cls._clean_fragment(part) for part in parts if cls._clean_fragment(part)]
        return []

    def _normalize_channel_list(self, value: object) -> list[str]:
        if isinstance(value, str):
            lowered = value.lower()
            channels = self._extract_channels(lowered=lowered)
            if channels:
                return channels
            rough_tokens = [
                self._clean_fragment(token).lower()
                for token in re.split(r"[,/\n|;·\s]+", value)
            ]
            rough_lowered = " ".join(token for token in rough_tokens if token)
            return self._extract_channels(lowered=rough_lowered)

        if isinstance(value, list):
            lowered = " ".join(self._clean_fragment(str(item)).lower() for item in value)
            return self._extract_channels(lowered=lowered)

        return []

    def _normalize_price_band_value(self, value: object) -> str | None:
        if isinstance(value, str):
            cleaned = self._clean_fragment(value).lower()
            if cleaned in {"low", "mid", "premium"}:
                return cleaned
            return self._extract_price_band(
                message=cleaned,
                lowered=cleaned,
                allow_plain_number=True,
            )
        if isinstance(value, (int, float)):
            return self._price_band_from_numeric(int(value))
        return None

    def _normalize_goal_value(self, value: object) -> str | None:
        if isinstance(value, str):
            cleaned = self._clean_fragment(value).lower()
            if cleaned in {"reach", "inquiry", "purchase"}:
                return cleaned
            return self._extract_goal(lowered=cleaned)
        return None

    @staticmethod
    def _dedupe_updates(updates: list[SlotUpdate]) -> list[SlotUpdate]:
        deduped: list[SlotUpdate] = []
        seen: set[tuple[str, str]] = set()
        for update in updates:
            key = (update.path, repr(update.value))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(update)
        return deduped

    @staticmethod
    def _extract_features(*, message: str, require_keyword: bool = True) -> list[str]:
        if require_keyword and "특징" not in message and "장점" not in message and "핵심" not in message:
            return []
        if not require_keyword:
            has_delimiter = bool(re.search(r"[,/\n|;·]", message))
            if not has_delimiter:
                tokens = [ChatOrchestrator._clean_fragment(token) for token in re.split(r"\s+", message)]
                tokens = [token for token in tokens if len(token) >= 2 and token not in {"그리고", "또한", "및"}]
                if len(tokens) < 3:
                    return []
                pair_suffixes = {
                    "흡수",
                    "포뮬러",
                    "사용감",
                    "지속력",
                    "보습",
                    "발색",
                    "커버",
                    "밀착",
                    "성분",
                }
                merged: list[str] = []
                index = 0
                while index < len(tokens):
                    if index + 1 < len(tokens) and tokens[index + 1] in pair_suffixes:
                        merged.append(f"{tokens[index]} {tokens[index + 1]}")
                        index += 2
                        continue
                    merged.append(tokens[index])
                    index += 1
                return ChatOrchestrator._filter_feature_terms(merged)

        candidate = message
        for token in ("특징", "장점", "핵심"):
            if token in candidate:
                candidate = candidate.split(token, maxsplit=1)[-1]
        candidate = re.sub(r"^\s*(?:은|는|:)+\s*", "", candidate)
        parts = re.split(r"[,\n/|;·]+", candidate)
        cleaned = [ChatOrchestrator._clean_fragment(part) for part in parts]
        return ChatOrchestrator._filter_feature_terms(cleaned)

    @classmethod
    def _extract_price_band(
        cls,
        *,
        message: str,
        lowered: str,
        allow_plain_number: bool = False,
    ) -> str | None:
        if any(keyword in lowered for keyword in ("저가", "가성비", "저렴")):
            return "low"
        if any(keyword in lowered for keyword in ("중가", "중간 가격", "미드")):
            return "mid"
        if any(keyword in lowered for keyword in ("고가", "프리미엄", "고급")):
            return "premium"

        manwon_tier_match = re.search(r"(\d+)\s*만\s*원?\s*대", message)
        if manwon_tier_match:
            numeric = int(manwon_tier_match.group(1)) * 10_000
            return cls._price_band_from_numeric(numeric)

        won_match = re.search(r"(\d[\d,]*)\s*원", message)
        if won_match:
            numeric = int(won_match.group(1).replace(",", ""))
            return cls._price_band_from_numeric(numeric)

        manwon_match = re.search(r"(\d+)\s*만\s*원", message)
        if manwon_match:
            numeric = int(manwon_match.group(1)) * 10_000
            return cls._price_band_from_numeric(numeric)

        symbol_match = re.search(r"(?:₩|￦)\s*(\d[\d,]*)", message)
        if symbol_match:
            numeric = int(symbol_match.group(1).replace(",", ""))
            return cls._price_band_from_numeric(numeric)

        has_price_context = any(
            keyword in lowered
            for keyword in ("가격", "금액", "비용", "원", "krw", "price")
        )
        if allow_plain_number or has_price_context:
            plain_numeric_pattern = (
                r"(\d[\d,]{3,})" if has_price_context else r"^\s*(\d[\d,]{3,})\s*$"
            )
            plain_numeric_match = re.search(plain_numeric_pattern, message)
            if plain_numeric_match:
                numeric = int(plain_numeric_match.group(1).replace(",", ""))
                return cls._price_band_from_numeric(numeric)

        return None

    @staticmethod
    def _price_band_from_numeric(numeric: int) -> str:
        if numeric <= 30_000:
            return "low"
        if numeric <= 100_000:
            return "mid"
        return "premium"

    def _has_discount_premium_conflict(self, *, message: str, lowered: str, price_band: str) -> bool:
        if price_band != "premium":
            return False
        if not any(keyword in lowered for keyword in self.LOW_PRICE_CUE_KEYWORDS):
            return False
        numeric = self._extract_price_numeric_krw(message)
        if numeric is None:
            return False
        return numeric >= 100_000

    @staticmethod
    def _extract_price_numeric_krw(message: str) -> int | None:
        won_match = re.search(r"(\d[\d,]*)\s*원", message)
        if won_match:
            return int(won_match.group(1).replace(",", ""))

        manwon_match = re.search(r"(\d+)\s*만\s*원?", message)
        if manwon_match:
            return int(manwon_match.group(1)) * 10_000

        symbol_match = re.search(r"(?:₩|￦)\s*(\d[\d,]*)", message)
        if symbol_match:
            return int(symbol_match.group(1).replace(",", ""))

        plain_numeric_match = re.search(r"^\s*(\d[\d,]{3,})\s*$", message)
        if plain_numeric_match:
            return int(plain_numeric_match.group(1).replace(",", ""))

        return None

    @staticmethod
    def _looks_like_user_question(message: str) -> bool:
        stripped = message.strip()
        if not stripped:
            return False
        lowered = stripped.lower()
        question_tokens = (
            "왜",
            "어떻게",
            "뭐",
            "무슨",
            "무엇",
            "필요해",
            "필요해요",
            "필요한가",
            "필요할까",
            "말이 돼",
            "맞아",
            "맞나요",
            "가능",
            "되나요",
            "인가요",
            "일까",
            "인가",
        )
        has_question_token = any(token in lowered for token in question_tokens)

        if "?" in stripped or "？" in stripped:
            normalized = re.sub(r"[?？!.,]", "", stripped).strip()
            tokens = [token for token in re.split(r"\s+", normalized) if token]
            # "아이폰?" 같은 짧은 단답은 질문으로 보지 않는다.
            if len(tokens) == 1 and len(normalized) <= 12 and not has_question_token:
                return False
            return True

        return has_question_token

    def _looks_like_delegate_request(self, message: str) -> bool:
        lowered = message.strip().lower()
        if not lowered:
            return False
        return any(keyword in lowered for keyword in self.DELEGATE_KEYWORDS)

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

    def _infer_update_for_expected_path(
        self,
        *,
        message: str,
        lowered: str,
        expected_path: str,
        slots: BriefSlots,
    ) -> SlotUpdate | None:
        cleaned = self._clean_fragment(message)
        if len(cleaned) < 2:
            return None
        is_question = self._looks_like_user_question(message)

        if expected_path == "product.name":
            if is_question:
                return None
            if len(cleaned) > 40:
                return None
            return SlotUpdate(path="product.name", value=cleaned, confidence=0.62)

        if expected_path == "product.category":
            if is_question:
                return None
            inferred_category = self._infer_category(lowered)
            if inferred_category:
                return SlotUpdate(path="product.category", value=inferred_category, confidence=0.67)
            if len(cleaned) <= 40 and "," not in cleaned:
                return SlotUpdate(path="product.category", value=cleaned, confidence=0.58)
            return None

        if expected_path == "target.who":
            if is_question:
                return None
            return SlotUpdate(path="target.who", value=cleaned, confidence=0.55)

        if expected_path == "target.why":
            if is_question:
                return None
            return SlotUpdate(path="target.why", value=cleaned, confidence=0.55)

        if expected_path == "product.price_band":
            price_band = self._extract_price_band(
                message=message,
                lowered=lowered,
                allow_plain_number=True,
            )
            if price_band and not self._has_discount_premium_conflict(
                message=message,
                lowered=lowered,
                price_band=price_band,
            ):
                return SlotUpdate(path="product.price_band", value=price_band, confidence=0.62)
            return None

        if expected_path == "channel.channels":
            if self._looks_like_delegate_request(message):
                recommended = self._recommend_channels(slots=slots)
                merged_channels = self._merge_unique(
                    slots.channel.channels,
                    recommended,
                    limit=2,
                )
                if merged_channels == slots.channel.channels:
                    return None
                return SlotUpdate(path="channel.channels", value=merged_channels, confidence=0.66)
            channels = self._extract_channels(lowered=lowered)
            if not channels:
                rough_tokens = [
                    self._clean_fragment(token).lower()
                    for token in re.split(r"[,/\n|;·\s]+", message)
                ]
                rough_lowered = " ".join(token for token in rough_tokens if token)
                channels = self._extract_channels(lowered=rough_lowered)
            if not channels:
                return None
            merged_channels = self._merge_unique(slots.channel.channels, channels, limit=2)
            if merged_channels == slots.channel.channels:
                return None
            return SlotUpdate(path="channel.channels", value=merged_channels, confidence=0.6)

        if expected_path == "goal.weekly_goal":
            goal = self._extract_goal(lowered=lowered)
            if goal:
                return SlotUpdate(path="goal.weekly_goal", value=goal, confidence=0.62)
            return None

        if expected_path == "product.features":
            extracted_features = self._extract_features(
                message=message,
                require_keyword=False,
            )
            if not extracted_features:
                token_fallback = self._clean_fragment(message)
                blocked_keywords = ("제품명", "카테고리", "가격", "타겟", "채널", "목표", "이유")
                token_count = len([part for part in re.split(r"\s+", token_fallback) if part])
                if (
                    token_fallback
                    and token_fallback.lower() not in self.FEATURE_FALLBACK_STOPWORDS
                    and not any(keyword in token_fallback for keyword in blocked_keywords)
                    and 1 <= token_count <= 3
                ):
                    extracted_features = [token_fallback]
            if not extracted_features:
                return None
            merged_features = self._merge_unique(slots.product.features, extracted_features, limit=6)
            if merged_features == slots.product.features:
                return None
            return SlotUpdate(path="product.features", value=merged_features, confidence=0.58)

        return None

    def _recommend_channels(self, *, slots: BriefSlots) -> list[str]:
        category = (slots.product.category or "").strip().lower()
        name = (slots.product.name or "").strip().lower()

        if any(keyword in category for keyword in ("푸드", "식품", "외식", "레스토랑", "프랜차이즈")):
            return ["Instagram", "YouTube"]
        if any(keyword in name for keyword in ("피자", "치킨", "버거", "카페")):
            return ["Instagram", "YouTube"]
        if any(keyword in category for keyword in ("뷰티", "스킨", "패션")):
            return ["Instagram", "YouTube Shorts"]
        return ["Instagram", "Naver"]

    def _first_missing_path(self, slots: BriefSlots) -> str | None:
        gate = self.evaluate_gate(slots)
        if not gate.missing_required:
            return None
        return gate.missing_required[0]

    def _is_paths_satisfied(self, *, slots: BriefSlots, paths: tuple[str, ...]) -> bool:
        for path in paths:
            if path == "product.features":
                if len(slots.product.features) < 3:
                    return False
                continue
            if path == "channel.channels":
                if not (1 <= len(slots.channel.channels) <= 2):
                    return False
                continue

            value = self._get_path_value(slots=slots, path=path)
            if self._is_empty(value):
                return False
        return True

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
        cleaned = cleaned.strip("[](){}")
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.rstrip(".,!?;:")
        for suffix in ("입니다", "이에요", "예요", "입니다.", "이에요.", "예요."):
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)].strip()
        cleaned = cleaned.rstrip(".,!?;:")
        return cleaned

    @classmethod
    def _filter_feature_terms(cls, candidates: list[str]) -> list[str]:
        normalized: list[str] = []
        for candidate in candidates:
            cleaned = cls._clean_fragment(candidate)
            if len(cleaned) < 2:
                continue
            lowered = cleaned.lower()
            if lowered in cls.FEATURE_FALLBACK_STOPWORDS:
                continue
            normalized.append(cleaned)
        return normalized

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
        elif update.path == "product.image_url":
            slots.product.image_url = str(update.value)
        elif update.path == "product.image_context":
            slots.product.image_context = str(update.value)
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
