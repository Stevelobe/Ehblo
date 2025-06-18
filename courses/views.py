# courses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Count, Q, Max # Explicitly import Max for clarity
from django.db import transaction
import json

# NEW IMPORT: For function-based login requirement
from django.contrib.auth.decorators import login_required

from .models import Course, Subject, Module, Content, TextContent, VideoContent, ImageContent, FileContent, Enrollment
from users.models import CustomUser
from .forms import CourseForm, ModuleForm, TextContentForm, VideoContentForm, ImageContentForm, FileContentForm, ContentForm
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse, Http404

# Remove 'from courses import models' if you're not using 'models.Course' directly.
# You already have 'from .models import ...' at the top, which is preferred.
# If you don't remove it and it's not used, it won't cause an error, but it's redundant.
# from courses import models


# Mixins for permissions
class InstructorRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user is an instructor.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == 'instructor'

class CourseOwnerRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user is the instructor of the course.
    It tries to find the course from different kwargs or linked objects.
    """
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated or user.user_type != 'instructor':
            return False

        course_id = None
        if 'pk' in self.kwargs:
            # For CourseUpdateView, CourseDeleteView
            course_id = self.kwargs['pk']
        elif 'course_id' in self.kwargs:
            # For ModuleCreateUpdateView
            course_id = self.kwargs['course_id']
        elif 'module_id' in self.kwargs:
            # For ContentCreateUpdateView, ContentDeleteView
            try:
                module = Module.objects.get(id=self.kwargs['module_id'])
                course_id = module.course.id
            except Module.DoesNotExist:
                return False
        elif 'content_id' in self.kwargs:
            # For ContentDeleteView potentially by content_id directly, and for mark/unmark complete views
            try:
                content = Content.objects.get(id=self.kwargs['content_id'])
                course_id = content.module.course.id
            except Content.DoesNotExist:
                return False
        elif 'enrollment_id' in self.kwargs: # Added for CoursePlayer and mark/unmark views
            try:
                enrollment = Enrollment.objects.get(id=self.kwargs['enrollment_id'])
                course_id = enrollment.course.id
            except Enrollment.DoesNotExist:
                return False


        if course_id:
            try:
                course = Course.objects.get(id=course_id)
                return course.instructor == user
            except Course.DoesNotExist:
                return False
        return False # No course ID found in kwargs


# --- Public Course Views ---
class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 10

    def get_queryset(self):
        # Only show published courses
        queryset = super().get_queryset().filter(is_published=True)

        # Filter by subject
        subject_slug = self.kwargs.get('subject_slug')
        if subject_slug:
            subject = get_object_or_404(Subject, slug=subject_slug)
            queryset = queryset.filter(subject=subject)

        # Search functionality
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(overview__icontains=query) |
                Q(instructor__username__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct()

        return queryset.annotate(num_modules=Count('modules')).order_by('-created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.annotate(total_courses=Count('courses', filter=Q(courses__is_published=True)))
        context['current_subject_slug'] = self.kwargs.get('subject_slug')
        context['query'] = self.request.GET.get('q', '')
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        # Only allow access to published courses unless the user is the instructor
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and self.request.user.user_type == 'instructor':
            # Instructors can see their unpublished courses
            return queryset
        return queryset.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        user_is_enrolled = False
        enrollment = None

        if self.request.user.is_authenticated:
            # Check if the user is an instructor and the owner of the course
            # Instructors of their own courses also implicitly "have access" to the chat
            if self.request.user.user_type == 'instructor' and course.instructor == self.request.user:
                # We'll use 'user_is_enrolled' to mean 'has access to chat/course content' for templates
                user_is_enrolled = True
            elif self.request.user.user_type == 'student':
                # For students, check for actual enrollment
                try:
                    enrollment = Enrollment.objects.get(student=self.request.user, course=course)
                    user_is_enrolled = True
                except Enrollment.DoesNotExist:
                    user_is_enrolled = False

        context['user_is_enrolled'] = user_is_enrolled
        context['enrollment'] = enrollment
        return context

# --- Instructor Dashboard & Course Management ---
class InstructorDashboardView(LoginRequiredMixin, InstructorRequiredMixin, ListView):
    model = Course
    template_name = 'courses/instructor_dashboard.html'
    context_object_name = 'courses'
    paginate_by = 10

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user).annotate(num_modules=Count('modules'))

class CourseCreateView(LoginRequiredMixin, InstructorRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('instructor_dashboard')

    def form_valid(self, form):
        form.instance.instructor = self.request.user # Assign the current instructor
        messages.success(self.request, "Course created successfully!")
        return super().form_valid(form)

class CourseUpdateView(LoginRequiredMixin, InstructorRequiredMixin, CourseOwnerRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'

    def get_success_url(self):
        messages.success(self.request, "Course updated successfully!")
        return reverse_lazy('course_detail', args=[self.object.id, self.object.slug])

class CourseDeleteView(LoginRequiredMixin, InstructorRequiredMixin, CourseOwnerRequiredMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('instructor_dashboard')

    def form_valid(self, form):
        messages.success(self.request, "Course deleted successfully!")
        return super().form_valid(form)


# Module Management
class ModuleCreateUpdateView(LoginRequiredMixin, InstructorRequiredMixin, CourseOwnerRequiredMixin, View):
    template_name = 'courses/module_form.html'
    module_form = ModuleForm

    def get_object(self):
        # Get module if updating, otherwise None
        module_id = self.kwargs.get('pk')
        return get_object_or_404(Module, pk=module_id, course_id=self.kwargs['course_id']) if module_id else None

    def get(self, request, course_id, pk=None): # pk is for module_id here
        course = get_object_or_404(Course, id=course_id, instructor=request.user)
        module = self.get_object()
        form = self.module_form(instance=module)
        return render(request, self.template_name, {'form': form, 'course': course, 'module': module})

    def post(self, request, course_id, pk=None): # pk is for module_id here
        course = get_object_or_404(Course, id=course_id, instructor=request.user)
        module = self.get_object()
        form = self.module_form(request.POST, instance=module)

        if form.is_valid():
            new_module = form.save(commit=False)
            new_module.course = course
            # Auto-assign order if not provided
            if new_module.order is None:
                max_order = course.modules.aggregate(Max('order'))['order__max'] # Use Max('field_name')['field_name__max']
                new_module.order = (max_order or 0) + 1
            new_module.save()
            messages.success(request, "Module saved successfully!")
            return redirect('course_detail', pk=course.id, slug=course.slug)
        return render(request, self.template_name, {'form': form, 'course': course, 'module': module})

class ModuleDeleteView(LoginRequiredMixin, InstructorRequiredMixin, CourseOwnerRequiredMixin, DeleteView):
    model = Module
    template_name = 'courses/module_confirm_delete.html'

    def get_success_url(self):
        module = self.get_object()
        messages.success(self.request, "Module deleted successfully!")
        return reverse_lazy('course_detail', args=[module.course.id, module.course.slug])


# --- Content Management (Generalized Create/Update View) ---
# Renamed from ContentCreateUpdateView for clarity, aligns with URL structure
class ModuleContentCreateUpdateView(LoginRequiredMixin, InstructorRequiredMixin, CourseOwnerRequiredMixin, View):
    template_name = 'courses/manage/content_update.html' # Changed to the specific template for content editing

    def get_content_model(self, model_name):
        try:
            # Ensure the model name is lowercase for consistency with URL patterns
            return apps.get_model('courses', model_name.capitalize())
        except LookupError:
            raise Http404(f"Content type '{model_name}' not found.")

    def get_content_form_class(self, model_name):
        """Helper to get the correct form class based on model_name."""
        if model_name == 'textcontent':
            return TextContentForm
        elif model_name == 'videocontent':
            return VideoContentForm
        elif model_name == 'imagecontent':
            return ImageContentForm
        elif model_name == 'filecontent':
            return FileContentForm
        return None # Should not happen if model_name is valid

    def get_content_object(self, content_id):
        return get_object_or_404(Content, id=content_id)

    def get(self, request, module_id, model_name, pk=None): # pk is for content_id
        module = get_object_or_404(Module, id=module_id, course__instructor=request.user)
        content_item = None
        form = None # Form for specific content type (e.g., ImageContentForm)
        content_obj = None # Content instance (generic foreign key container)

        if pk: # If updating existing content
            content_obj = self.get_content_object(pk)
            # Ensure the content belongs to the correct module and instructor
            if content_obj.module != module:
                raise Http404("Content does not belong to this module.")
            # Ensure the fetched item's model name matches the URL's model_name
            if content_obj.item.__class__.__name__.lower() != model_name:
                messages.error(request, 'Mismatch between content type in URL and existing content.')
                return redirect(reverse_lazy('course_detail', kwargs={'pk': module.course.pk}))

            content_item = content_obj.item # Get the actual TextContent, VideoContent etc. object
            item_form = self.get_content_form_class(model_name)(instance=content_item)
            content_meta_form = ContentForm(instance=content_obj) # Form for general Content model fields
        else: # If creating new content
            item_form = self.get_content_form_class(model_name)()
            content_meta_form = ContentForm() # New, empty form for generic Content model fields

        if item_form is None:
            raise Http404(f"Invalid content type: {model_name}")

        context = {
            'module': module,
            'item_form': item_form, # Renamed for clarity in template (was 'form')
            'content_form': content_meta_form, # Renamed for clarity in template (was 'content_meta_form')
            'model_name': model_name,
            'content_obj': content_obj, # The Content instance
            'item': content_item, # The specific content item (e.g., ImageContent instance)
        }
        return render(request, self.template_name, context)

    def post(self, request, module_id, model_name, pk=None):
        module = get_object_or_404(Module, id=module_id, course__instructor=request.user)
        content_item = None
        content_obj = None

        if pk: # Update existing content
            content_obj = self.get_content_object(pk)
            if content_obj.module != module:
                raise Http404("Content does not belong to this module.")
            if content_obj.item.__class__.__name__.lower() != model_name:
                messages.error(request, 'Mismatch between content type in URL and existing content. Cannot update.')
                return redirect(reverse_lazy('course_detail', kwargs={'pk': module.course.pk, 'slug': module.course.slug}))

            content_item = content_obj.item # Get the actual TextContent, VideoContent etc. object
            item_form = self.get_content_form_class(model_name)(request.POST, request.FILES, instance=content_item)
            content_form = ContentForm(request.POST, instance=content_obj)
        else: # Create new content
            item_form = self.get_content_form_class(model_name)(request.POST, request.FILES)
            content_form = ContentForm(request.POST)

        if item_form is None:
            raise Http404(f"Invalid content type: {model_name}")

        if item_form.is_valid() and content_form.is_valid():
            # Use a transaction to ensure both saves succeed or fail together
            with transaction.atomic():
                content_item_instance = item_form.save() # Saves TextContent, VideoContent etc.

                if not pk: # If creating new Content object
                    content_type = ContentType.objects.get_for_model(content_item_instance)

                    # --- CRITICAL CHANGE HERE: Determine order BEFORE creating Content object ---
                    # Get the order value from the ContentForm.
                    # .get('order') will return None if the field is not present or blank
                    form_provided_order = content_form.cleaned_data.get('order')

                    # Determine the final order to use for the new content item
                    if form_provided_order is None: # If the user didn't explicitly provide an order
                        # Calculate the next available order for this module
                        result = module.contents.aggregate(max_order=Max('order'))
                        current_max_order = result.get('max_order')
                        # Start from 1 if no contents, else max + 1
                        determined_order = (current_max_order or 0) + 1
                    else:
                        # Use the order provided by the form if it was explicitly set
                        determined_order = form_provided_order
                    # --- END CRITICAL CHANGE ---

                    # Create the new Content object with the determined order
                    content_obj = Content(
                        module=module,
                        content_type=content_type,
                        object_id=content_item_instance.id,
                        title=content_form.cleaned_data['title'],
                        order=determined_order # Use the order we just determined
                    )
                    content_obj.save()
                else: # If updating existing Content object
                    # For updates, the order from content_form is typically directly applied
                    content_obj.title = content_form.cleaned_data['title']
                    content_obj.order = content_form.cleaned_data['order'] # Use the order from the form
                    content_obj.save()

            messages.success(request, f"{model_name.capitalize()} content saved successfully!")
            return redirect('course_detail', pk=module.course.id, slug=module.course.slug)

        # If forms are invalid, re-render the template with errors
        context = {
            'module': module,
            'item_form': item_form,
            'content_form': content_form,
            'model_name': model_name,
            'content_obj': content_obj,
            'item': content_item,
        }
        messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, context)

class ContentDeleteView(LoginRequiredMixin, InstructorRequiredMixin, CourseOwnerRequiredMixin, DeleteView):
    model = Content
    template_name = 'courses/content_confirm_delete.html'
    pk_url_kwarg = 'content_id' # Ensure this matches your URL conf

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Ensure the content belongs to the current instructor's course
        if obj.module.course.instructor != self.request.user:
            raise Http404("You are not authorized to delete this content.")
        return obj

    def get_success_url(self):
        content = self.get_object()
        messages.success(self.request, "Content deleted successfully!")
        return reverse_lazy('course_detail', args=[content.module.course.id, content.module.course.slug])


# --- Student Views ---

# Apply the login_required decorator for function-based views
@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Ensure enrollment happens via POST for security and idempotence
    if request.method != 'POST':
        messages.error(request, "Enrollment must be done via a form submission (POST request).")
        return redirect('course_detail', pk=course.id, slug=course.slug)

    # Restrict enrollment to students only
    if request.user.user_type != 'student':
        messages.error(request, "Only students can enroll in courses.")
        return redirect('course_detail', pk=course.id, slug=course.slug)

    # Check if the user is already enrolled
    if Enrollment.objects.filter(student=request.user, course=course).exists():
        messages.info(request, f"You are already enrolled in '{course.title}'.")
        # Redirect to 'my_courses' if already enrolled to provide a consistent experience
        return redirect('my_courses')

    # --- MODIFIED LOGIC: Directly enroll regardless of course.price ---
    try:
        Enrollment.objects.create(student=request.user, course=course)
        messages.success(request, f"Congratulations! You have successfully enrolled in '{course.title}'!")
        # Redirect the user to their list of enrolled courses
        return redirect('my_courses')
    except Exception as e:
        messages.error(request, f"Failed to enroll in '{course.title}'. An unexpected error occurred: {e}")
        # Redirect back to the course detail page on error
        return redirect('course_detail', pk=course.id, slug=course.slug)

class EnrolledCourseListView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'courses/my_courses.html'
    context_object_name = 'enrollments'

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user).select_related('course').order_by('-enrolled_at')

class CoursePlayerView(LoginRequiredMixin, DetailView):
    model = Enrollment
    template_name = 'courses/course_player.html'
    context_object_name = 'enrollment'
    pk_url_kwarg = 'enrollment_id' # We're using enrollment_id as pk for lookup

    def get_object(self, queryset=None):
        enrollment_id = self.kwargs.get('enrollment_id')
        enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=self.request.user)
        return enrollment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollment = self.get_object()
        course = enrollment.course

        # Ensure module_id and content_id are valid for this enrollment and course
        module_id = self.kwargs.get('module_id')
        content_id = self.kwargs.get('content_id')

        selected_module = None
        selected_content = None

        if module_id:
            try:
                selected_module = course.modules.get(id=module_id)
            except Module.DoesNotExist:
                # If module_id is provided but doesn't exist, raise 404
                raise Http404("Module not found in this course.")

        # If no module_id or content_id, try to get the first content of the first module
        if not selected_module:
            if course.modules.exists():
                selected_module = course.modules.order_by('order').first()
                if selected_module and selected_module.contents.exists():
                    selected_content = selected_module.contents.order_by('order').first()
        elif selected_module and not content_id: # If module selected, but no specific content, get first content
            if selected_module.contents.exists():
                selected_content = selected_module.contents.order_by('order').first()
        elif selected_module and content_id: # If both module and content IDs are provided
            try:
                selected_content = selected_module.contents.get(id=content_id)
            except Content.DoesNotExist:
                raise Http404("Content not found in this module.")

        context['course'] = course
        context['selected_module'] = selected_module
        context['selected_content'] = selected_content
        context['modules'] = course.modules.prefetch_related('contents__item') # Eager load contents and their specific item

        # Calculate progress for display
        total_contents_in_course = course.modules.aggregate(total=Count('contents'))['total'] or 0 # Ensure it's not None
        context['total_contents_in_course'] = total_contents_in_course

        context['completed_content_ids'] = list(enrollment.completed_contents.values_list('id', flat=True))
        context['progress_percentage'] = enrollment.get_progress()

        return context

# API endpoint for updating content order (requires JavaScript for drag-and-drop)
class ContentOrderView(LoginRequiredMixin, InstructorRequiredMixin, View):
    def post(self, request, module_id):
        module = get_object_or_404(Module, id=module_id, course__instructor=request.user)

        data = request.body.decode('utf-8')
        try:
            content_order = json.loads(data) # Expects a list of {id: content_id, order: new_order}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

        for item in content_order:
            try:
                content_obj = Content.objects.get(id=item['id'], module=module)
                content_obj.order = item['order']
                content_obj.save()
            except Content.DoesNotExist:
                return JsonResponse({'error': f"Content with ID {item['id']} not found or not in module"}, status=404)
            except KeyError:
                return JsonResponse({'error': 'Missing ID or order in payload'}, status=400)

        return JsonResponse({'message': 'Content order updated successfully'})

# --- NEW: Mark/Unmark Content as Complete Views ---
@login_required
def mark_content_as_complete(request, enrollment_id, module_id, content_id):
    if request.method == 'POST':
        enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
        course = enrollment.course

        # Basic validation: Ensure the module and content belong to this course and module
        module = get_object_or_404(Module, id=module_id, course=course)
        selected_content = get_object_or_404(Content, id=content_id, module=module)

        # Check if the content is not already completed
        if not enrollment.completed_contents.filter(id=selected_content.id).exists():
            enrollment.completed_contents.add(selected_content)
            messages.success(request, f"'{selected_content.title}' marked as completed!")
        else:
            messages.info(request, f"'{selected_content.title}' was already completed.")

        # Redirect back to the course player, to the specific content just marked
        return redirect('course_player_content',
                        enrollment_id=enrollment.id,
                        module_id=module.id,
                        content_id=selected_content.id)
    else:
        messages.error(request, "Invalid request method. Please use POST to mark content as complete.")
        # Redirect back to the course player in case of GET request (or other non-POST)
        return redirect('course_player_content',
                        enrollment_id=enrollment_id,
                        module_id=module_id,
                        content_id=content_id)

@login_required
def unmark_content_as_complete(request, enrollment_id, module_id, content_id):
    if request.method == 'POST':
        enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
        course = enrollment.course

        module = get_object_or_404(Module, id=module_id, course=course)
        selected_content = get_object_or_404(Content, id=content_id, module=module)

        if enrollment.completed_contents.filter(id=selected_content.id).exists():
            enrollment.completed_contents.remove(selected_content)
            messages.success(request, f"'{selected_content.title}' unmarked as completed!")
        else:
            messages.info(request, f"'{selected_content.title}' was not marked completed.")

        return redirect('course_player_content',
                        enrollment_id=enrollment.id,
                        module_id=module.id,
                        content_id=selected_content.id)
    else:
        messages.error(request, "Invalid request method. Please use POST to unmark content as complete.")
        return redirect('course_player_content',
                        enrollment_id=enrollment_id,
                        module_id=module_id,
                        content_id=content_id)