from safedelete.admin import SafeDeleteAdmin, SafeDeleteAdminFilter, highlight_deleted


class BaseModelAdmin(SafeDeleteAdmin):
    list_display = ((highlight_deleted, "highlight_deleted_field")
                    + SafeDeleteAdmin.list_display
                    + ("is_active", "created_at", "updated_at"))
    list_filter = (SafeDeleteAdminFilter,) + SafeDeleteAdmin.list_filter
    field_to_highlight = "id"
