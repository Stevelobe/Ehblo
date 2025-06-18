# courses/models.py
from django.db import models
from django.conf import settings
from taggit.managers import TaggableManager
from django.template.loader import render_to_string
from django.utils.text import slugify

# Imports for GenericForeignKey and aggregate functions (important!)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Count, Max # <--- Make sure these are here

import os # ADD THIS IMPORT! This is necessary for os.path.basename and os.path.splitext


class Subject(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Course(models.Model):
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='courses_created',
                                   limit_choices_to={'user_type': 'instructor'})
    subject = models.ForeignKey(Subject,
                                  on_delete=models.CASCADE,
                                  related_name='courses')
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    overview = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # 0 for free courses
    is_published = models.BooleanField(default=False)
    tags = TaggableManager(blank=True)

    # ADD THIS LINE FOR THE COURSE THUMBNAIL IMAGE
    image = models.ImageField(upload_to='course_thumbnails/', null=True, blank=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('course_detail', args=[str(self.id), self.slug])


class Module(models.Model):
    course = models.ForeignKey(Course,
                               on_delete=models.CASCADE,
                               related_name='modules')
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, blank=True, null=True)

    class Meta:
        ordering = ('order',)
        unique_together = ('course', 'title')

    def __str__(self):
        return f'{self.order}. {self.title}'


class Content(models.Model):
    module = models.ForeignKey(Module,
                               on_delete=models.CASCADE,
                               related_name='contents')
    title = models.CharField(max_length=250, blank=True)
    order = models.PositiveIntegerField(default=0, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    content_type = models.ForeignKey(ContentType,
                                     on_delete=models.CASCADE,
                                     limit_choices_to={'model__in':(
                                         'textcontent',
                                         'videocontent',
                                         'imagecontent',
                                         'filecontent')})
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ('order',)
        unique_together = ('module', 'order')
        verbose_name_plural = "Contents" # Added verbose_name_plural

    def __str__(self):
        # Fallback for item if it's somehow None or doesn't have a __class__
        item_name = self.item.__class__.__name__ if self.item else "Unknown Content Type"
        return f"{self.module.course.title} - {self.module.title} - {item_name} ({self.title})"

    def render(self):
        # Safely get the lowercased model name for the template path
        template_name = self.item.__class__.__name__.lower()
        return render_to_string(f'courses/content/{template_name}.html', {'item': self.item})


class TextContent(models.Model):
    # Field name changed from 'content' to 'text'
    text = models.TextField(verbose_name="Text Content") # <--- CORRECTED LINE

    class Meta:
        verbose_name_plural = "Text Contents"
        verbose_name = "Text Content"
    def __str__(self):
        return f"Text Content (ID: {self.id})"

class VideoContent(models.Model):
    # Field name changed from 'video_url' to 'url'
    url = models.URLField(help_text="Paste YouTube, Vimeo, or direct video URL.", verbose_name="Video URL") # <--- CORRECTED LINE

    class Meta:
        verbose_name_plural = "Video Contents"
        verbose_name = "Video Content"
    def __str__(self):
        return f"Video Content (ID: {self.id})"

class ImageContent(models.Model):
    image = models.ImageField(upload_to='course_images/', verbose_name="Image File")

    class Meta:
        verbose_name_plural = "Image Contents"
        verbose_name = "Image Content"
    def __str__(self):
        return f"Image Content (ID: {self.id})"

class FileContent(models.Model):
    file = models.FileField(upload_to='course_files/', verbose_name="File Attachment")

    class Meta:
        verbose_name_plural = "File Contents"
        verbose_name = "File Content"
    def __str__(self):
        return f"File Content (ID: {self.id})"

    # ADD THESE TWO PROPERTIES!
    @property
    def filename(self):
        """Returns just the filename from the path (e.g., 'document.pdf' from 'uploads/files/document.pdf')."""
        return os.path.basename(self.file.name)

    @property
    def file_extension(self):
        """Returns the file extension (e.g., 'pdf' from 'document.pdf')."""
        name, extension = os.path.splitext(self.file.name)
        return extension.lstrip('.').lower() # Remove the leading dot and make it lowercase


class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='enrollments',
                                   limit_choices_to={'user_type': 'student'})
    course = models.ForeignKey(Course,
                               on_delete=models.CASCADE,
                               related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_contents = models.ManyToManyField(Content, blank=True, related_name='completed_by_students')

    class Meta:
        unique_together = ('student', 'course')
        verbose_name_plural = "Enrollments"

    def __str__(self):
        return f'{self.student.username} enrolled in {self.course.title}'

    def get_progress(self):
        # Using Count imported directly from django.db.models
        total_contents = self.course.modules.aggregate(total=Count('contents'))['total']
        if not total_contents:
            return 0
        completed_count = self.completed_contents.count()
        return (completed_count / total_contents) * 100