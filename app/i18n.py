"""Internationalisation (i18n) for the application UI.

A tiny home-grown translation layer: two flat dictionaries (English and
Simplified Chinese) keyed by dot-separated identifiers, a global *current
language*, and a small publish/subscribe mechanism so widgets can rebuild
themselves when the language changes.

Usage in UI code::

    from app.i18n import tr
    ttk.Button(parent, text=tr("btn.save"))

Parameterised strings use ``str.format`` kwargs::

    tr("msg.ship_confirm", order_id=5)
"""

from __future__ import annotations

from typing import Callable


SUPPORTED_LANGUAGES = ("en", "zh")
DEFAULT_LANGUAGE = "en"


# English strings. Kept as the reference set; the Chinese dictionary mirrors
# exactly the same keys.
_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # ---- App / window ----
        "app.title": "Inventory & Order Management",
        "app.appbar": "Inventory & Orders",
        "app.appbar_subtitle": "Track stock and customer orders in one place",

        # ---- Tabs ----
        "tab.inventory": "  Inventory  ",
        "tab.orders": "  Orders  ",
        "tab.statistics": "  Statistics  ",

        # ---- Language button ----
        "lang.switch_to": "中文",  # shown when current is English

        # ---- Inventory view ----
        "inv.search_placeholder": "Search by code or name...",
        "inv.filter_color": "Color",
        "inv.filter_size": "Size",
        "inv.filter_stock": "Stock",
        "filter.all": "All",
        "filter.in_stock": "In stock",
        "filter.out_of_stock": "Out of stock",
        "filter.status_new": "New",
        "filter.status_shipped": "Shipped",
        "inv.clear_filters": "Clear",
        "inv.title": "Inventory",
        "inv.subtitle": "Track products, stock-in and stock-out movements.",
        "btn.add_product": "+ Add Product",
        "btn.view_details": "View Details",
        "btn.edit": "Edit",
        "btn.delete": "Delete",
        "btn.refresh": "Refresh",
        "col.code": "Code",
        "col.name": "Name",
        "col.price": "Price",
        "col.stock": "Stock",
        "col.product": "Product",
        "col.color": "Color",
        "col.size": "Size",
        "col.qty": "Qty",
        "col.subtotal": "Subtotal",
        "col.date": "Date",
        "col.cost": "Cost",
        "col.note": "Note",
        "col.customer": "Customer",
        "col.type": "Type",
        "col.info": "Info",
        "col.order_no": "Order #",
        "col.order_date": "Order Date",
        "col.status": "Status",
        "col.shipped_date": "Shipped Date",
        "col.total": "Total",
        "col.units": "Units",
        "col.revenue": "Revenue",
        "err.no_selection": "No selection",
        "err.select_product": "Please select a product first.",
        "err.select_order": "Please select an order first.",
        "err.cannot_delete": "Cannot delete",
        "confirm.delete_product_title": "Delete product",
        "confirm.delete_product_msg": "Delete this product and all its stock movements?\nThis cannot be undone.",

        # ---- Orders view ----
        "ord.search_placeholder": "Search by customer or order #...",
        "ord.filter_status": "Status",
        "ord.filter_from": "From",
        "ord.filter_to": "To",
        "ord.clear_filters": "Clear",
        "ord.title": "Orders",
        "ord.subtitle": "Record customer orders and confirm shipment when dispatched.",
        "btn.new_order": "+ New Order",
        "btn.view": "View",
        "btn.mark_shipped": "Mark as Shipped",
        "info.already_shipped_title": "Already shipped",
        "info.already_shipped_msg": "This order is already shipped.",
        "confirm.ship_title": "Ship order",
        "confirm.ship_msg": "Mark order #{order_id} as shipped?",
        "confirm.delete_order_title": "Delete order",
        "confirm.delete_order_msg": "Delete this order?",
        "err.cannot_ship": "Cannot ship",

        # ---- Order dialog ----
        "dlg.order_title_new": "New Order",
        "dlg.order_subtitle": "Choose products, colors and quantities for this customer.",
        "lbl.customer": "Customer:",
        "lbl.order_date": "Order date:",
        "lbl.product": "Product:",
        "lbl.color": "Color:",
        "lbl.size": "Size:",
        "lbl.qty": "Qty:",
        "lbl.price": "Price:",
        "sect.line_items": "Line items",
        "btn.add_line": "Add line",
        "btn.remove": "Remove",
        "btn.close": "Close",
        "btn.save_order": "Save Order",
        "btn.cancel": "Cancel",
        "btn.save": "Save",
        "status.label": "Status: {status}",
        "status.shipped_on": "   (shipped {date})",
        "err.no_products_title": "No products",
        "err.no_products_msg": "Add products in the Inventory tab first.",
        "err.pick_product_title": "Pick product",
        "err.pick_product_msg": "Select a product first.",
        "err.bad_qty_title": "Bad quantity",
        "err.bad_qty_msg": "Quantity must be an integer.",
        "err.bad_price_title": "Bad price",
        "err.bad_price_msg": "Price must be a number.",
        "total.label": "Total: {total}",
        "err.missing_customer_title": "Missing customer",
        "err.missing_customer_msg": "Customer name is required.",
        "err.no_items_title": "No items",
        "err.no_items_msg": "Add at least one line item.",
        "info.saved_title": "Saved",
        "info.saved_msg": "Order #{order_id} created with status 'New'.\nUse Mark as Shipped when it is dispatched.",

        # ---- Product dialog ----
        "dlg.add_product": "Add Product",
        "dlg.edit_product": "Edit Product",
        "dlg.product_subtitle": "Code, price and image identify the product; variants are its color/size combos.",
        "lbl.code": "Code:",
        "lbl.name": "Name:",
        "lbl.base_price": "Base Price:",
        "lbl.image": "Image:",
        "lbl.no_image": "(no image)",
        "btn.browse": "Browse...",
        "lbl.variants": "Variants (one per line, format:  Color; Size)",
        "sect.add_variant": "Add variant",
        "lbl.pick_color": "Color:",
        "lbl.pick_size": "Size:",
        "btn.add_variant": "Add",
        "hint.color_new": "or type a new color",
        "hint.size_new": "or type a new size",
        "sect.existing_variants": "Variants",
        "btn.remove_variant": "Remove",
        "info.no_variants": "No variants yet. Add at least one color/size combo.",
        "err.duplicate_variant_title": "Duplicate variant",
        "err.duplicate_variant_msg": "This color/size combination is already in the list.",
        "err.variant_empty_title": "Empty variant",
        "err.variant_empty_msg": "Please choose or type a color and a size.",
        "err.missing_data_title": "Missing data",
        "err.missing_data_msg": "Code and Name are required.",
        "err.invalid_price_title": "Invalid price",
        "err.invalid_price_msg": "Base price must be a number.",
        "err.image_error_title": "Image error",
        "err.could_not_save_title": "Could not save",

        # ---- Product detail ----
        "detail.title": "Product Details",
        "detail.code": "Code  {code}",
        "detail.base_price": "Base price  {price}",
        "detail.units_in_stock": "units in stock",
        "tab.stock_in": "  Stock-In  ",
        "tab.stock_out": "  Stock-Out  ",
        "tab.history": "  History  ",
        "sect.current_stock": "Current stock",
        "sect.recent_stock_out": "Recent stock-out",
        "lbl.unit_cost": "Unit Cost:",
        "lbl.date": "Date:",
        "lbl.note": "Note:",
        "lbl.quantity": "Quantity:",
        "btn.add": "Add",
        "btn.remove_stock": "Remove Stock",
        "err.invalid_qty_title": "Invalid quantity",
        "err.invalid_qty_int_msg": "Quantity must be an integer.",
        "err.invalid_qty_pos_msg": "Quantity must be greater than zero.",
        "err.invalid_cost_title": "Invalid cost",
        "err.invalid_cost_msg": "Unit cost must be a number.",

        # ---- Statistics ----
        "stats.title": "Statistics",
        "stats.subtitle": "Sales performance based on shipped orders.",
        "lbl.period": "Period:",
        "period.this_week": "This Week",
        "period.this_month": "This Month",
        "period.this_quarter": "This Quarter",
        "period.custom": "Custom Range",
        "lbl.from": "From:",
        "lbl.to": "To:",
        "btn.apply": "Apply",
        "metric.revenue": "Revenue",
        "metric.orders_shipped": "Orders Shipped",
        "metric.units_sold": "Units Sold",
        "sect.top_products": "Top products",
        "sect.trend": "Trend",
        "btn.mark_new": "Mark as New",
        "info.not_shipped_title": "Not shipped",
        "info.not_shipped_msg": "This order is not shipped yet.",
        "confirm.unship_title": "Revert shipment",
        "confirm.unship_msg": "Revert order #{order_id} back to New?\nStock will be returned to inventory.",
        "err.cannot_unship": "Cannot revert",
        "dlg.image_viewer": "Image viewer",
        "dlg.image_viewer_hint": "Click anywhere or press Esc to close",

        # ---- Widgets ----
        "widget.no_image": "No image",
        "status.new": "New",
        "status.shipped": "Shipped",
        "file.select_image_title": "Select product image",
        "file.images": "Images",
        "file.all_files": "All files",
    },
    "zh": {
        # ---- 应用 / 窗口 ----
        "app.title": "库存与订单管理",
        "app.appbar": "库存与订单",
        "app.appbar_subtitle": "一处管理库存与客户订单",

        # ---- 选项卡 ----
        "tab.inventory": "  库存  ",
        "tab.orders": "  订单  ",
        "tab.statistics": "  统计  ",

        # ---- 语言按钮 ----
        "lang.switch_to": "EN",

        # ---- 库存视图 ----
        "inv.search_placeholder": "按编码或名称搜索...",
        "inv.filter_color": "颜色",
        "inv.filter_size": "尺码",
        "inv.filter_stock": "库存",
        "filter.all": "全部",
        "filter.in_stock": "有库存",
        "filter.out_of_stock": "无库存",
        "filter.status_new": "新建",
        "filter.status_shipped": "已发货",
        "inv.clear_filters": "清除",
        "inv.title": "库存",
        "inv.subtitle": "管理商品、入库与出库记录。",
        "btn.add_product": "+ 添加商品",
        "btn.view_details": "查看详情",
        "btn.edit": "编辑",
        "btn.delete": "删除",
        "btn.refresh": "刷新",
        "col.code": "编码",
        "col.name": "名称",
        "col.price": "价格",
        "col.stock": "库存",
        "col.product": "商品",
        "col.color": "颜色",
        "col.size": "尺码",
        "col.qty": "数量",
        "col.subtotal": "小计",
        "col.date": "日期",
        "col.cost": "成本",
        "col.note": "备注",
        "col.customer": "客户",
        "col.type": "类型",
        "col.info": "信息",
        "col.order_no": "订单号",
        "col.order_date": "下单日期",
        "col.status": "状态",
        "col.shipped_date": "发货日期",
        "col.total": "总计",
        "col.units": "销量",
        "col.revenue": "营收",
        "err.no_selection": "未选择",
        "err.select_product": "请先选择一个商品。",
        "err.select_order": "请先选择一个订单。",
        "err.cannot_delete": "无法删除",
        "confirm.delete_product_title": "删除商品",
        "confirm.delete_product_msg": "删除此商品及其所有库存变动记录?\n此操作无法撤销。",

        # ---- 订单视图 ----
        "ord.search_placeholder": "按客户或订单号搜索...",
        "ord.filter_status": "状态",
        "ord.filter_from": "从",
        "ord.filter_to": "至",
        "ord.clear_filters": "清除",
        "ord.title": "订单",
        "ord.subtitle": "记录客户订单,并在发货时确认。",
        "btn.new_order": "+ 新建订单",
        "btn.view": "查看",
        "btn.mark_shipped": "标记为已发货",
        "info.already_shipped_title": "已发货",
        "info.already_shipped_msg": "此订单已发货。",
        "confirm.ship_title": "发货",
        "confirm.ship_msg": "将订单 #{order_id} 标记为已发货?",
        "confirm.delete_order_title": "删除订单",
        "confirm.delete_order_msg": "删除此订单?",
        "err.cannot_ship": "无法发货",

        # ---- 订单对话框 ----
        "dlg.order_title_new": "新建订单",
        "dlg.order_subtitle": "为此客户选择商品、颜色和数量。",
        "lbl.customer": "客户:",
        "lbl.order_date": "下单日期:",
        "lbl.product": "商品:",
        "lbl.color": "颜色:",
        "lbl.size": "尺码:",
        "lbl.qty": "数量:",
        "lbl.price": "价格:",
        "sect.line_items": "订单明细",
        "btn.add_line": "添加行",
        "btn.remove": "移除",
        "btn.close": "关闭",
        "btn.save_order": "保存订单",
        "btn.cancel": "取消",
        "btn.save": "保存",
        "status.label": "状态: {status}",
        "status.shipped_on": "   (发货日期 {date})",
        "err.no_products_title": "无商品",
        "err.no_products_msg": "请先在库存选项卡中添加商品。",
        "err.pick_product_title": "选择商品",
        "err.pick_product_msg": "请先选择一个商品。",
        "err.bad_qty_title": "数量无效",
        "err.bad_qty_msg": "数量必须是整数。",
        "err.bad_price_title": "价格无效",
        "err.bad_price_msg": "价格必须是数字。",
        "total.label": "总计: {total}",
        "err.missing_customer_title": "缺少客户",
        "err.missing_customer_msg": "必须填写客户名称。",
        "err.no_items_title": "无明细",
        "err.no_items_msg": "请至少添加一行明细。",
        "info.saved_title": "已保存",
        "info.saved_msg": "订单 #{order_id} 已创建,状态为'新建'。\n发货时请使用'标记为已发货'。",

        # ---- 商品对话框 ----
        "dlg.add_product": "添加商品",
        "dlg.edit_product": "编辑商品",
        "dlg.product_subtitle": "编码、价格和图片用于标识商品;变体是颜色/尺码组合。",
        "lbl.code": "编码:",
        "lbl.name": "名称:",
        "lbl.base_price": "基础价格:",
        "lbl.image": "图片:",
        "lbl.no_image": "(无图片)",
        "btn.browse": "浏览...",
        "lbl.variants": "变体 (每行一个,格式: 颜色; 尺码)",
        "sect.add_variant": "添加变体",
        "lbl.pick_color": "颜色:",
        "lbl.pick_size": "尺码:",
        "btn.add_variant": "添加",
        "hint.color_new": "或输入新颜色",
        "hint.size_new": "或输入新尺码",
        "sect.existing_variants": "变体列表",
        "btn.remove_variant": "移除",
        "info.no_variants": "暂无变体。请至少添加一个颜色/尺码组合。",
        "err.duplicate_variant_title": "重复变体",
        "err.duplicate_variant_msg": "此颜色/尺码组合已在列表中。",
        "err.variant_empty_title": "变体为空",
        "err.variant_empty_msg": "请选择或输入颜色和尺码。",
        "err.missing_data_title": "缺少数据",
        "err.missing_data_msg": "编码和名称为必填项。",
        "err.invalid_price_title": "价格无效",
        "err.invalid_price_msg": "基础价格必须是数字。",
        "err.image_error_title": "图片错误",
        "err.could_not_save_title": "无法保存",

        # ---- 商品详情 ----
        "detail.title": "商品详情",
        "detail.code": "编码  {code}",
        "detail.base_price": "基础价格  {price}",
        "detail.units_in_stock": "件库存",
        "tab.stock_in": "  入库  ",
        "tab.stock_out": "  出库  ",
        "tab.history": "  历史  ",
        "sect.current_stock": "当前库存",
        "sect.recent_stock_out": "近期出库",
        "lbl.unit_cost": "单位成本:",
        "lbl.date": "日期:",
        "lbl.note": "备注:",
        "lbl.quantity": "数量:",
        "btn.add": "添加",
        "btn.remove_stock": "移出库存",
        "err.invalid_qty_title": "数量无效",
        "err.invalid_qty_int_msg": "数量必须是整数。",
        "err.invalid_qty_pos_msg": "数量必须大于零。",
        "err.invalid_cost_title": "成本无效",
        "err.invalid_cost_msg": "单位成本必须是数字。",

        # ---- 统计 ----
        "stats.title": "统计",
        "stats.subtitle": "基于已发货订单的销售业绩。",
        "lbl.period": "周期:",
        "period.this_week": "本周",
        "period.this_month": "本月",
        "period.this_quarter": "本季度",
        "period.custom": "自定义范围",
        "lbl.from": "从:",
        "lbl.to": "至:",
        "btn.apply": "应用",
        "metric.revenue": "营收",
        "metric.orders_shipped": "已发货订单",
        "metric.units_sold": "销量",
        "sect.top_products": "热门商品",
        "sect.trend": "趋势",
        "btn.mark_new": "标记为新建",
        "info.not_shipped_title": "未发货",
        "info.not_shipped_msg": "此订单尚未发货。",
        "confirm.unship_title": "撤销发货",
        "confirm.unship_msg": "将订单 #{order_id} 恢复为新建?\n库存将返还。",
        "err.cannot_unship": "无法撤销",
        "dlg.image_viewer": "图片查看器",
        "dlg.image_viewer_hint": "点击任意位置或按 Esc 关闭",

        # ---- 控件 ----
        "widget.no_image": "无图片",
        "status.new": "新建",
        "status.shipped": "已发货",
        "file.select_image_title": "选择商品图片",
        "file.images": "图片",
        "file.all_files": "所有文件",
    },
}

# Current language code. Module-global on purpose: a single language applies
# to the whole application at once.
_current_language: str = DEFAULT_LANGUAGE

# Callbacks invoked (in registration order) whenever the language changes.
# Widgets register their rebuild routine here so a single toggle refreshes
# the entire UI.
_change_listeners: list[Callable[[], None]] = []


def get_language() -> str:
    """Return the current language code (``"en"`` or ``"zh"``)."""

    return _current_language


def set_language(lang: str) -> None:
    """Switch the active language and notify all registered listeners.

    If ``lang`` is unknown or equal to the current language this is a no-op
    (listeners are not notified), which keeps toggling idempotent.
    """

    global _current_language
    if lang not in _STRINGS or lang == _current_language:
        return
    _current_language = lang
    for callback in list(_change_listeners):
        callback()


def toggle_language() -> None:
    """Flip between English and Simplified Chinese."""

    set_language("zh" if _current_language == "en" else "en")


def on_change(callback: Callable[[], None]) -> None:
    """Register ``callback`` to run whenever the language changes."""

    if callback not in _change_listeners:
        _change_listeners.append(callback)


def tr(key: str, **kwargs) -> str:
    """Return the translated string for ``key`` in the current language.

    Unknown keys fall back to the English entry, then to the key itself, so a
    missing translation never raises — it just shows something recognisable
    during development. ``kwargs`` are forwarded to ``str.format``.
    """

    table = _STRINGS.get(_current_language, _STRINGS[DEFAULT_LANGUAGE])
    text = table.get(key)
    if text is None:
        text = _STRINGS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
