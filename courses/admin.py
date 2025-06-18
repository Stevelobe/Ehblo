# courses/admin.py

from django.contrib import admin
from django.apps import apps
from django.contrib.contenttypes.admin import GenericStackedInline
from .models import Subject, Course, Module, Content, TextContent, VideoContent, ImageContent, FileContent, Enrollment
from users.models import CustomUser

# --- 1. Inline for the 'Content' object within specific content type forms ---
class ContentGenericInline(GenericStackedInline):
    model = Content
    fields = ('module', 'title', 'order')
    extra = 1
    max_num = 1
    can_delete = False

# --- 2. Admin classes for specific content types (now including the generic inline) ---

@admin.register(TextContent)
class TextContentAdmin(admin.ModelAdmin):
    list_display = ('__str__',)
    inlines = [ContentGenericInline]

@admin.register(VideoContent)
class VideoContentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'display_url') # CHANGE: Use a method for 'url'
    inlines = [ContentGenericInline]

    # NEW: Method to display the URL
    def display_url(self, obj):
        return obj.url
    display_url.short_description = 'Video URL' # Sets the column header in the admin list


@admin.register(ImageContent)
class ImageContentAdmin(admin.ModelAdmin):
    list_display = ('__str__',)
    inlines = [ContentGenericInline]

@admin.register(FileContent)
class FileContentAdmin(admin.ModelAdmin):
    list_display = ('__str__',)
    inlines = [ContentGenericInline]

# --- 3. Inlines for Course and Module management ---

class ModuleContentInline(admin.StackedInline):
    model = Content
    extra = 0
    fields = ('title', 'order', 'content_type', 'object_id')
    ordering = ['order']

class ModuleInline(admin.StackedInline):
    model = Module
    extra = 0
    show_change_link = True
    ordering = ['order']

# --- 4. Main Admin registrations ---

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course']
    search_fields = ['title']
    inlines = [ModuleContentInline]
    ordering = ['order']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'instructor', 'price', 'is_published', 'created']
    list_filter = ['is_published', 'created', 'subject']
    search_fields = ['title', 'overview', 'instructor__username']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline]
    raw_id_fields = ('instructor',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "instructor":
            kwargs["queryset"] = CustomUser.objects.filter(user_type='instructor')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at')
    list_filter = ('enrolled_at', 'course', 'student')
    search_fields = ('student__username', 'course__title')
    raw_id_fields = ('student', 'course')