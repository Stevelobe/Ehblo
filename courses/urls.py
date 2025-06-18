# courses/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Public Course List & Detail
    path('', views.CourseListView.as_view(), name='course_list'),
    path('subject/<slug:subject_slug>/', views.CourseListView.as_view(), name='course_list_by_subject'),
    path('<int:pk>/<slug:slug>/', views.CourseDetailView.as_view(), name='course_detail'),

    # Instructor Dashboard & Course CRUD
    path('instructor-dashboard/', views.InstructorDashboardView.as_view(), name='instructor_dashboard'),
    path('create/', views.CourseCreateView.as_view(), name='course_create'),
    path('<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),

    # Module CRUD
    path('<int:course_id>/module/create/', views.ModuleCreateUpdateView.as_view(), name='module_create'),
    path('<int:course_id>/module/<int:pk>/edit/', views.ModuleCreateUpdateView.as_view(), name='module_update'),
    # Use 'pk' for module ID directly in URL for consistency with ModuleDeleteView
    path('module/<int:pk>/delete/', views.ModuleDeleteView.as_view(), name='module_delete'),

    # --- Content CRUD (using generic relations) ---
    # Create new content for a module: /courses/<module_id>/content/add/<content_type_name>/
    path('<int:module_id>/content/add/<str:model_name>/',
          views.ModuleContentCreateUpdateView.as_view(),
          name='module_content_create'),

    # Edit existing content: /courses/<module_id>/content/<content_id>/edit/<content_type_name>/
    path('<int:module_id>/content/<int:pk>/edit/<str:model_name>/',
          views.ModuleContentCreateUpdateView.as_view(),
          name='module_content_update'),

    # Delete content: /courses/content/<content_id>/delete/
    # Changed 'pk' to 'content_id' to match pk_url_kwarg in ContentDeleteView
    path('content/<int:content_id>/delete/',
          views.ContentDeleteView.as_view(),
          name='content_delete'),

    # Content Ordering API
    path('<int:module_id>/content/order/', views.ContentOrderView.as_view(), name='content_order'),

    # Student Enrollment & Course Player
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('my-courses/', views.EnrolledCourseListView.as_view(), name='my_courses'),
    # Course Player URL: /my-courses/<enrollment_id>/module/<module_id>/content/<content_id>/
    path('my-courses/<int:enrollment_id>/', views.CoursePlayerView.as_view(), name='course_player_home'), # Start of course
    path('my-courses/<int:enrollment_id>/module/<int:module_id>/', views.CoursePlayerView.as_view(), name='course_player_module'),
    path('my-courses/<int:enrollment_id>/module/<int:module_id>/content/<int:content_id>/', views.CoursePlayerView.as_view(), name='course_player_content'),

    # NEW: URLs for marking/unmarking content as complete
    # These paths are intentionally distinct from the course player navigation paths
    # to handle the POST request for marking/unmarking.
    path('my-courses/<int:enrollment_id>/module/<int:module_id>/content/<int:content_id>/mark-complete/',
         views.mark_content_as_complete,
         name='mark_content_as_complete'),
    path('my-courses/<int:enrollment_id>/module/<int:module_id>/content/<int:content_id>/unmark-complete/',
         views.unmark_content_as_complete,
         name='unmark_content_as_complete'),
]