"""Internationalisation (EN / ZH) for the web app.

Same key set as the desktop app's ``i18n.py``. The active language is stored
in the Flask session (``session['lang']``) and defaults to English. The Jinja
filter ``tr`` lets templates call ``{{ 'btn.save'|tr }}``; parameterised
strings use ``{{ 'total.label'|tr(total='12.50') }}``.
"""

from __future__ import annotations

from flask import session

DEFAULT_LANGUAGE = "en"
SUPPORTED = ("en", "zh")

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app.appbar": "Inventory & Orders",
        "app.appbar_subtitle": "Track stock and customer orders in one place",
        "tab.inventory": "Inventory",
        "tab.orders": "Orders",
        "tab.statistics": "Statistics",
        "tab.stock_in": "Stock-In",
        "tab.stock_out": "Stock-Out",
        "tab.history": "History",
        "lang.switch_to": "中文",

        "login.title": "Sign in",
        "login.username": "Username",
        "login.password": "Password",
        "login.submit": "Sign in",
        "login.bad": "Wrong username or password.",
        "login.signed_out": "You have been signed out.",

        "menu.change_password": "Change password",
        "menu.manage_users": "Manage users",
        "menu.backup": "Download backup",
        "menu.reset_db": "Reset all data",

        "profile.old_password": "Current password",
        "profile.new_password": "New password",
        "profile.confirm_password": "Confirm new password",

        "admin.users_subtitle": "Create accounts and manage access",
        "admin.create_user": "Create user",
        "admin.make_admin": "Administrator (can manage users and reset data)",
        "admin.existing_users": "Existing users",

        "err.wrong_password": "Current password is incorrect.",
        "err.password_short": "Password must be at least 4 characters.",
        "err.password_mismatch": "New passwords do not match.",
        "err.invalid_input": "Please fill in all fields (password min 4 chars).",
        "err.user_exists": "This username is already taken.",
        "err.cannot_delete_self": "You cannot delete your own account.",
        "err.confirm_reset": "Please type RESET to confirm.",

        "info.password_changed": "Password changed.",
        "info.user_created": "User '{username}' created.",
        "info.user_deleted": "User deleted.",
        "info.db_reset": "All data has been cleared. User accounts were kept.",

        "confirm.delete_user_msg": "Delete this user account?",
        "confirm.reset_db_msg": "This will permanently delete ALL products, orders and stock movements.",
        "confirm.reset_db_hint": "Type RESET in the field below to confirm. User accounts are NOT deleted.",

        "inv.title": "Inventory",
        "inv.subtitle": "Track products, stock-in and stock-out movements.",
        "inv.search_placeholder": "Search by code or name...",
        "inv.filter_color": "Color",
        "inv.filter_size": "Size",
        "inv.filter_stock": "Stock",
        "inv.clear_filters": "Clear",

        "filter.all": "All",
        "filter.in_stock": "In stock",
        "filter.out_of_stock": "Out of stock",
        "filter.status_new": "New",
        "filter.status_shipped": "Shipped",

        "ord.title": "Orders",
        "ord.subtitle": "Record customer orders and confirm shipment when dispatched.",
        "ord.search_placeholder": "Search by customer or order #...",
        "ord.filter_status": "Status",
        "ord.filter_from": "From",
        "ord.filter_to": "To",
        "ord.clear_filters": "Clear",

        "dlg.order_title_new": "New Order",
        "dlg.order_subtitle": "Choose products, colors and quantities for this customer.",
        "dlg.add_product": "Add Product",
        "dlg.edit_product": "Edit Product",
        "dlg.product_subtitle": "Code, price and image identify the product; variants are its color/size combos.",
        "dlg.image_viewer": "Image viewer",

        "lbl.customer": "Customer",
        "lbl.order_date": "Order date",
        "lbl.product": "Product",
        "lbl.color": "Color",
        "lbl.size": "Size",
        "lbl.qty": "Qty",
        "lbl.price": "Price",
        "lbl.code": "Code",
        "lbl.name": "Name",
        "lbl.base_price": "Base Price",
        "lbl.image": "Image",
        "lbl.unit_cost": "Unit Cost",
        "lbl.date": "Date",
        "lbl.note": "Note",
        "lbl.quantity": "Quantity",
        "lbl.pick_color": "Color",
        "lbl.pick_size": "Size",
        "lbl.period": "Period",
        "lbl.from": "From",
        "lbl.to": "To",
        "lbl.no_image": "(no image)",

        "sect.line_items": "Line items",
        "sect.add_variant": "Add variant",
        "sect.existing_variants": "Variants",
        "sect.current_stock": "Current stock",
        "sect.recent_stock_out": "Recent stock-out",
        "sect.top_products": "Top products",
        "sect.trend": "Trend",

        "btn.add_product": "+ Add Product",
        "btn.view_details": "View Details",
        "btn.edit": "Edit",
        "btn.delete": "Delete",
        "btn.refresh": "Refresh",
        "btn.new_order": "+ New Order",
        "btn.view": "View",
        "btn.mark_shipped": "Mark as Shipped",
        "btn.mark_new": "Mark as New",
        "btn.close": "Close",
        "btn.cancel": "Cancel",
        "btn.save": "Save",
        "btn.browse": "Browse...",
        "btn.add_line": "Add line",
        "btn.remove": "Remove",
        "btn.add_variant": "Add",
        "btn.remove_variant": "Remove",
        "btn.add": "Add",
        "btn.remove_stock": "Remove Stock",
        "btn.save_order": "Save Order",
        "btn.apply": "Apply",
        "btn.sign_out": "Sign out",

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

        "stats.title": "Statistics",
        "stats.subtitle": "Sales performance based on shipped orders.",

        "metric.revenue": "Revenue",
        "metric.net_profit": "Net Profit",
        "metric.orders_shipped": "Orders Shipped",
        "metric.units_sold": "Units Sold",

        "period.this_week": "This Week",
        "period.this_month": "This Month",
        "period.this_quarter": "This Quarter",
        "period.custom": "Custom Range",

        "status.new": "New",
        "status.shipped": "Shipped",
        "status.label": "Status: {status}",
        "status.shipped_on": "(shipped {date})",
        "total.label": "Total: {total}",
        "detail.units_in_stock": "units in stock",
        "widget.no_image": "No image",

        "info.no_variants": "No variants yet. Add at least one color/size combo.",
        "info.saved_msg": "Order #{order_id} created with status 'New'.",

        "confirm.delete_product_msg": "Delete this product and all its stock movements? This cannot be undone.",
        "confirm.delete_order_msg": "Delete this order?",
        "confirm.delete_shipped_order_msg": "Delete shipped order #{order_id}? Its stock will be returned to inventory and it will be removed from statistics.",
        "confirm.ship_msg": "Mark order #{order_id} as shipped? Stock will be reduced.",
        "confirm.ship_shortage_msg": "Insufficient stock for some items:",
        "confirm.unship_msg": "Revert order #{order_id} back to New? Stock will be returned.",
    },
    "zh": {
        "app.appbar": "库存与订单",
        "app.appbar_subtitle": "一处管理库存与客户订单",
        "tab.inventory": "库存",
        "tab.orders": "订单",
        "tab.statistics": "统计",
        "tab.stock_in": "入库",
        "tab.stock_out": "出库",
        "tab.history": "历史",
        "lang.switch_to": "EN",

        "login.title": "登录",
        "login.username": "用户名",
        "login.password": "密码",
        "login.submit": "登录",
        "login.bad": "用户名或密码错误。",
        "login.signed_out": "您已退出登录。",

        "menu.change_password": "修改密码",
        "menu.manage_users": "用户管理",
        "menu.backup": "下载数据备份",
        "menu.reset_db": "清空所有数据",

        "profile.old_password": "当前密码",
        "profile.new_password": "新密码",
        "profile.confirm_password": "确认新密码",

        "admin.users_subtitle": "创建账号并管理访问权限",
        "admin.create_user": "创建用户",
        "admin.make_admin": "管理员(可管理用户和清空数据)",
        "admin.existing_users": "现有用户",

        "err.wrong_password": "当前密码不正确。",
        "err.password_short": "密码至少需要 4 个字符。",
        "err.password_mismatch": "两次输入的新密码不一致。",
        "err.invalid_input": "请填写所有字段(密码至少 4 个字符)。",
        "err.user_exists": "该用户名已被占用。",
        "err.cannot_delete_self": "不能删除自己的账号。",
        "err.confirm_reset": "请输入 RESET 以确认。",

        "info.password_changed": "密码已修改。",
        "info.user_created": "用户 “{username}” 已创建。",
        "info.user_deleted": "用户已删除。",
        "info.db_reset": "所有数据已清空。用户账号已保留。",

        "confirm.delete_user_msg": "删除此用户账号?",
        "confirm.reset_db_msg": "此操作将永久删除所有商品、订单和库存记录。",
        "confirm.reset_db_hint": "在下方输入 RESET 以确认。用户账号不会被删除。",

        "inv.title": "库存",
        "inv.subtitle": "管理商品、入库与出库记录。",
        "inv.search_placeholder": "按编码或名称搜索...",
        "inv.filter_color": "颜色",
        "inv.filter_size": "尺码",
        "inv.filter_stock": "库存",
        "inv.clear_filters": "清除",

        "filter.all": "全部",
        "filter.in_stock": "有库存",
        "filter.out_of_stock": "无库存",
        "filter.status_new": "新建",
        "filter.status_shipped": "已发货",

        "ord.title": "订单",
        "ord.subtitle": "记录客户订单,并在发货时确认。",
        "ord.search_placeholder": "按客户或订单号搜索...",
        "ord.filter_status": "状态",
        "ord.filter_from": "从",
        "ord.filter_to": "至",
        "ord.clear_filters": "清除",

        "dlg.order_title_new": "新建订单",
        "dlg.order_subtitle": "为此客户选择商品、颜色和数量。",
        "dlg.add_product": "添加商品",
        "dlg.edit_product": "编辑商品",
        "dlg.product_subtitle": "编码、价格和图片用于标识商品;变体是颜色/尺码组合。",
        "dlg.image_viewer": "图片查看器",

        "lbl.customer": "客户",
        "lbl.order_date": "下单日期",
        "lbl.product": "商品",
        "lbl.color": "颜色",
        "lbl.size": "尺码",
        "lbl.qty": "数量",
        "lbl.price": "价格",
        "lbl.code": "编码",
        "lbl.name": "名称",
        "lbl.base_price": "基础价格",
        "lbl.image": "图片",
        "lbl.unit_cost": "单位成本",
        "lbl.date": "日期",
        "lbl.note": "备注",
        "lbl.quantity": "数量",
        "lbl.pick_color": "颜色",
        "lbl.pick_size": "尺码",
        "lbl.period": "周期",
        "lbl.from": "从",
        "lbl.to": "至",
        "lbl.no_image": "(无图片)",

        "sect.line_items": "订单明细",
        "sect.add_variant": "添加变体",
        "sect.existing_variants": "变体列表",
        "sect.current_stock": "当前库存",
        "sect.recent_stock_out": "近期出库",
        "sect.top_products": "热门商品",
        "sect.trend": "趋势",

        "btn.add_product": "+ 添加商品",
        "btn.view_details": "查看详情",
        "btn.edit": "编辑",
        "btn.delete": "删除",
        "btn.refresh": "刷新",
        "btn.new_order": "+ 新建订单",
        "btn.view": "查看",
        "btn.mark_shipped": "标记为已发货",
        "btn.mark_new": "标记为新建",
        "btn.close": "关闭",
        "btn.cancel": "取消",
        "btn.save": "保存",
        "btn.browse": "浏览...",
        "btn.add_line": "添加行",
        "btn.remove": "移除",
        "btn.add_variant": "添加",
        "btn.remove_variant": "移除",
        "btn.add": "添加",
        "btn.remove_stock": "移出库存",
        "btn.save_order": "保存订单",
        "btn.apply": "应用",
        "btn.sign_out": "退出登录",

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

        "stats.title": "统计",
        "stats.subtitle": "基于已发货订单的销售业绩。",

        "metric.revenue": "营收",
        "metric.net_profit": "净利润",
        "metric.orders_shipped": "已发货订单",
        "metric.units_sold": "销量",

        "period.this_week": "本周",
        "period.this_month": "本月",
        "period.this_quarter": "本季度",
        "period.custom": "自定义范围",

        "status.new": "新建",
        "status.shipped": "已发货",
        "status.label": "状态: {status}",
        "status.shipped_on": "(发货日期 {date})",
        "total.label": "总计: {total}",
        "detail.units_in_stock": "件库存",
        "widget.no_image": "无图片",

        "info.no_variants": "暂无变体。请至少添加一个颜色/尺码组合。",
        "info.saved_msg": "订单 #{order_id} 已创建,状态为'新建'。",

        "confirm.delete_product_msg": "删除此商品及其所有库存变动记录?此操作无法撤销。",
        "confirm.delete_order_msg": "删除此订单?",
        "confirm.delete_shipped_order_msg": "删除已发货订单 #{order_id}?库存将返还,并从统计中移除。",
        "confirm.ship_msg": "将订单 #{order_id} 标记为已发货?库存将减少。",
        "confirm.ship_shortage_msg": "部分商品库存不足:",
        "confirm.unship_msg": "将订单 #{order_id} 恢复为新建?库存将返还。",
    },
}


def get_language() -> str:
    return session.get("lang", DEFAULT_LANGUAGE)


def set_language(lang: str) -> None:
    if lang in SUPPORTED:
        session["lang"] = lang


def tr(key: str, **kwargs) -> str:
    lang = get_language()
    table = _STRINGS.get(lang, _STRINGS[DEFAULT_LANGUAGE])
    text = table.get(key)
    if text is None:
        text = _STRINGS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
