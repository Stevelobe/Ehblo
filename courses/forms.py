# courses/forms.py
from django import forms
from .models import Course, Module, Content, TextContent, VideoContent, ImageContent, FileContent, Subject
from taggit.forms import TagWidget # Import TagWidget for better tag display/input

# --- Helper for consistent styling ---
def apply_common_widget_attrs(widget):
    """Applies common TailwindCSS classes to form widgets."""
    if 'class' not in widget.attrs:
        widget.attrs['class'] = ''
    # Append common classes if they aren't already present
    common_classes = 'w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-purple-500 focus:border-purple-500'
    for cls in common_classes.split():
        if cls not in widget.attrs['class']:
            widget.attrs['class'] += f' {cls}'
    widget.attrs['class'] = widget.attrs['class'].strip() # Clean up any leading/trailing spaces


# --- Course Forms ---
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['subject', 'title', 'slug', 'overview', 'price', 'is_published', 'tags', 'image']
        widgets = {
            'overview': forms.Textarea(attrs={'rows': 5}),
            'slug': forms.TextInput(attrs={'placeholder': 'Auto-generated if left blank'}),
            'title': forms.TextInput(),
            'price': forms.NumberInput(),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-purple-600'}),
            'tags': TagWidget(attrs={'placeholder': 'Enter tags separated by commas'}),
            'image': forms.ClearableFileInput(attrs={'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100'}),
            'subject': forms.Select(attrs={'class': 'block appearance-none w-full bg-white border border-gray-300 text-gray-700 py-2 px-3 pr-8 rounded-md leading-tight focus:outline-none focus:bg-white focus:border-purple-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tags'].required = False

        # Apply common styling to various input types, excluding those with specific custom widgets
        for field_name, field in self.fields.items():
            if field_name not in ['is_published', 'image', 'subject']:
                if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.Textarea, forms.Select, TagWidget)):
                    apply_common_widget_attrs(field.widget)


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order']
        widgets = {
            'title': forms.TextInput(),
            'description': forms.Textarea(attrs={'rows': 3}),
            'order': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.Textarea)):
                apply_common_widget_attrs(field.widget)

    def clean_order(self):
        order = self.cleaned_data.get('order')
        if order is None:
            return order
        if order < 0:
            raise forms.ValidationError("Order cannot be negative.")
        return order


# --- Consolidated and Corrected Content Forms ---
# This is the ContentForm that should be used everywhere for Content objects
class ContentForm(forms.ModelForm):
    class Meta:
        model = Content
        # Correct fields for the Content object (module, title, order)
        fields = ['module', 'title', 'order']
        widgets = {
            'title': forms.TextInput(),
            'order': forms.NumberInput(attrs={'min': 0}),
            'module': forms.Select(), # Module field is a Select widget
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'module':
                field.widget.attrs.update({'class': 'block appearance-none w-full bg-white border border-gray-300 text-gray-700 py-2 px-3 pr-8 rounded-md leading-tight focus:outline-none focus:bg-white focus:border-purple-500'})
            else: # Apply common styling to title and order fields
                 apply_common_widget_attrs(field.widget)


class TextContentForm(forms.ModelForm):
    class Meta:
        model = TextContent
        # CORRECTED FIELD NAME: 'content' to 'text'
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 10}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_common_widget_attrs(self.fields['text'].widget)


class VideoContentForm(forms.ModelForm):
    class Meta:
        model = VideoContent
        # CORRECTED FIELD NAME: 'video_url' to 'url'
        fields = ['url']
        widgets = {
            'url': forms.URLInput(attrs={'placeholder': 'Paste YouTube, Vimeo, or direct video URL'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_common_widget_attrs(self.fields['url'].widget)


class ImageContentForm(forms.ModelForm):
    class Meta:
        model = ImageContent
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'}),
        }
    # No common styling applied here, as ClearableFileInput has its own specific styling.


class FileContentForm(forms.ModelForm):
    class Meta:
        model = FileContent
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100'}),
        }
    # No common styling applied here, as ClearableFileInput has its own specific styling.