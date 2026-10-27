"""쇼핑 리스트 앱 (Streamlit).

요구사항은 PRD.md 참고.

상태 변경은 모두 위젯 콜백(on_click / on_change)에서 처리하고,
렌더링 함수는 session_state를 읽기만 한다.
"""

import re
import uuid
from datetime import datetime

import streamlit as st

MAX_NAME_LENGTH = 50
EMPTY_NAME_WARNING = "아이템 이름을 입력해 주세요."
TOO_LONG_WARNING = f"아이템 이름은 최대 {MAX_NAME_LENGTH}자까지 입력할 수 있어요."

# 앞뒤의 공백과 폭 없는 문자(ZWSP, ZWNJ, ZWJ, WORD JOINER, BOM).
# str.strip()은 폭 없는 문자를 지우지 않는다. 가운데 ZWJ는 이모지 조합(👨‍👩‍👧)에
# 쓰이므로 앞뒤에서만 지운다.
_EDGE_BLANKS = re.compile(r"^[\s​-‍⁠﻿]+|[\s​-‍⁠﻿]+$")


# ---------------------------------------------------------------------------
# 상태 / 데이터 모델
# ---------------------------------------------------------------------------

def init_state():
    """session_state 기본값을 초기화한다. (PRD 5장)

    주의: st.session_state.items 는 dict의 items() 메서드와 이름이 겹치므로
    항상 st.session_state["items"] 처럼 대괄호로 접근한다.
    """
    defaults = {
        "items": [],
        "editing_id": None,
        "add_warning": None,
        "edit_warning": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def make_item(name):
    """새 아이템 dict를 만든다."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "checked": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def validate_name(name):
    """이름을 정리하고 검증한다. (정리된 이름, 경고 메시지 또는 None)을 반환한다."""
    name = _EDGE_BLANKS.sub("", name or "")
    if not name:
        return name, EMPTY_NAME_WARNING
    if len(name) > MAX_NAME_LENGTH:
        return name, TOO_LONG_WARNING
    return name, None


def find_item(item_id):
    """id로 아이템을 찾는다. 없으면 None."""
    return next((it for it in st.session_state["items"] if it["id"] == item_id), None)


# ---------------------------------------------------------------------------
# 아이템 조작
# ---------------------------------------------------------------------------

def add_item(name):
    """아이템을 리스트 맨 아래에 추가한다. 성공 여부를 반환한다. (FR-1)"""
    name, warning = validate_name(name)
    st.session_state["add_warning"] = warning
    if warning:
        return False
    st.session_state["items"].append(make_item(name))
    return True


def update_item(item_id, new_name):
    """아이템 이름을 수정한다. 성공 여부를 반환한다. (FR-2)"""
    new_name, warning = validate_name(new_name)
    st.session_state["edit_warning"] = warning
    item = find_item(item_id)
    if warning or item is None:
        return False
    item["name"] = new_name
    return True


def delete_item(item_id):
    """아이템을 삭제한다. (FR-3)"""
    st.session_state["items"] = [
        it for it in st.session_state["items"] if it["id"] != item_id
    ]
    if st.session_state["editing_id"] == item_id:
        stop_edit()


def toggle_item(item_id):
    """아이템의 체크 상태를 체크박스 값과 맞춘다. (FR-4)"""
    item = find_item(item_id)
    if item is not None:
        item["checked"] = st.session_state[f"chk_{item_id}"]


def clear_checked():
    """체크된 아이템을 모두 삭제한다. (FR-3, P1)"""
    editing = find_item(st.session_state["editing_id"])
    if editing is not None and editing["checked"]:
        stop_edit()
    st.session_state["items"] = [
        it for it in st.session_state["items"] if not it["checked"]
    ]


# ---------------------------------------------------------------------------
# 콜백
# ---------------------------------------------------------------------------

def on_add():
    add_item(st.session_state["new_item_name"])


def start_edit(item_id):
    """수정 모드로 전환한다. 한 번에 하나의 아이템만 수정한다."""
    item = find_item(item_id)
    if item is None:
        return
    st.session_state["editing_id"] = item_id
    st.session_state["edit_warning"] = None
    st.session_state[f"edit_{item_id}"] = item["name"]


def stop_edit():
    st.session_state["editing_id"] = None
    st.session_state["edit_warning"] = None


def on_save(item_id):
    if update_item(item_id, st.session_state[f"edit_{item_id}"]):
        stop_edit()


# ---------------------------------------------------------------------------
# 화면 구성
# ---------------------------------------------------------------------------

def render_input():
    """아이템 입력창과 [추가] 버튼을 그린다. Enter로도 추가된다."""
    with st.form("add_form", clear_on_submit=True, border=False):
        cols = st.columns([0.8, 0.2], vertical_alignment="bottom")
        cols[0].text_input(
            "살 물건",
            key="new_item_name",
            placeholder="살 물건을 입력하세요...",
            max_chars=MAX_NAME_LENGTH,
            label_visibility="collapsed",
        )
        cols[1].form_submit_button(
            "추가", type="primary", on_click=on_add, use_container_width=True
        )

    if st.session_state["add_warning"]:
        st.warning(st.session_state["add_warning"])
        st.session_state["add_warning"] = None


def render_summary():
    """전체 / 남은 개수 요약을 그린다. (FR-5)"""
    items = st.session_state["items"]
    remaining = sum(not it["checked"] for it in items)
    st.caption(f"전체 {len(items)}개 · 남은 {remaining}개")


def render_item(item):
    """아이템 한 줄을 그린다: 체크박스 / 이름 / 수정 / 삭제."""
    item_id = item["id"]
    editing = st.session_state["editing_id"] == item_id
    # 수정 모드에서는 이름·저장·취소를 하나의 폼으로 묶어야 하므로(Enter로 저장)
    # 바깥 컬럼을 [체크박스 | 폼]으로 나누고 폼 안에서 같은 비율로 다시 나눈다.
    widths = [0.1, 0.9] if editing else [0.1, 0.7, 0.1, 0.1]
    cols = st.columns(widths, vertical_alignment="center", gap="small")

    # 위젯 key는 리스트 인덱스가 아닌 아이템 id로 만들어
    # 삭제 후에도 다른 아이템의 위젯 상태가 섞이지 않게 한다.
    # (폼 안의 위젯은 on_change 콜백을 쓸 수 없으므로 체크박스는 폼 밖에 둔다.)
    cols[0].checkbox(
        item["name"],
        value=item["checked"],
        key=f"chk_{item_id}",
        on_change=toggle_item,
        args=(item_id,),
        label_visibility="collapsed",
    )

    # 아이콘 버튼의 글자 라벨("수정" 등)은 CSS로 시각적으로만 숨겨
    # 스크린리더가 이모지 대신 라벨을 읽도록 한다.
    if editing:
        with cols[1].form(f"form_edit_{item_id}", border=False):
            inner = st.columns([0.7, 0.1, 0.1], vertical_alignment="center", gap="small")
            inner[0].text_input(
                "아이템 이름 수정",
                key=f"edit_{item_id}",
                max_chars=MAX_NAME_LENGTH,
                label_visibility="collapsed",
            )
            # Enter는 폼의 첫 번째 제출 버튼(저장)으로 처리된다.
            inner[1].form_submit_button("저장", icon="💾", key=f"save_{item_id}", help="저장",
                                        type="tertiary", on_click=on_save, args=(item_id,))
            inner[2].form_submit_button("취소", icon="✖️", key=f"cancel_{item_id}", help="취소",
                                        type="tertiary", on_click=stop_edit)
        if st.session_state["edit_warning"]:
            st.warning(st.session_state["edit_warning"])
    else:
        # st.text는 마크다운/HTML을 해석하지 않으므로 입력값이 그대로 보인다.
        # 완료 스타일(취소선)은 HTML에 이름을 넣지 않고, 컨테이너 key가 만드는
        # CSS 클래스(st-key-done-...)로 입힌다. → 이스케이프가 필요 없다.
        state = "done" if item["checked"] else "todo"
        cols[1].container(key=f"{state}-{item_id}").text(item["name"])
        cols[2].button("수정", icon="✏️", key=f"edit_btn_{item_id}", help="수정",
                       type="tertiary", on_click=start_edit, args=(item_id,))
        cols[3].button("삭제", icon="🗑️", key=f"del_{item_id}", help="삭제",
                       type="tertiary", on_click=delete_item, args=(item_id,))


def render_list():
    """아이템 목록을 그린다."""
    items = st.session_state["items"]
    if not items:
        st.info("쇼핑 리스트가 비어 있어요. 아이템을 추가해 보세요!")
        return

    if st.session_state.get("done_last"):
        # sorted는 안정 정렬이므로 같은 그룹 안에서는 추가한 순서가 유지된다.
        items = sorted(items, key=lambda it: it["checked"])

    st.divider()
    for item in items:
        render_item(item)
    st.divider()

    left, right = st.columns([0.5, 0.5], vertical_alignment="center")
    left.toggle("완료 항목 아래로", key="done_last")
    right.button(
        "완료 항목 모두 삭제",
        on_click=clear_checked,
        disabled=not any(it["checked"] for it in items),
        use_container_width=True,
    )


def inject_css():
    """최소한의 CSS. 사용자 입력은 포함하지 않는다."""
    st.markdown(
        """
        <style>
        /* 모바일(좁은 화면)에서도 행의 컬럼이 세로로 쌓이지 않게 한 줄 유지 */
        [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: 0 !important;
        }
        /* 긴 이름은 줄바꿈 */
        [class*="st-key-todo-"] [data-testid="stText"],
        [class*="st-key-done-"] [data-testid="stText"] {
            overflow-wrap: anywhere;
        }
        /* 완료 항목: 취소선 + 흐리게 (opacity라 라이트/다크 테마 모두 대응) */
        [class*="st-key-done-"] [data-testid="stText"] {
            text-decoration: line-through;
            opacity: 0.45;
        }
        /* 아이콘 버튼 가운데 정렬 */
        [class*="st-key-edit_btn_"], [class*="st-key-del_"],
        [class*="st-key-save_"], [class*="st-key-cancel_"] {
            display: flex; justify-content: center;
        }
        /* 아이콘 버튼의 글자 라벨은 화면에서만 숨기고 스크린리더에는 남긴다 */
        [class*="st-key-edit_btn_"] button [data-testid="stMarkdownContainer"],
        [class*="st-key-del_"] button [data-testid="stMarkdownContainer"],
        [class*="st-key-save_"] button [data-testid="stMarkdownContainer"],
        [class*="st-key-cancel_"] button [data-testid="stMarkdownContainer"] {
            position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
            overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="쇼핑 리스트", page_icon="🛒", layout="centered")
    init_state()
    inject_css()

    st.title("🛒 쇼핑 리스트")
    render_input()
    render_summary()
    render_list()


main()
