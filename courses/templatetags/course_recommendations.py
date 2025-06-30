# courses/templatetags/course_recommendations.py

from django import template
from courses.models import Course, Enrollment # Import Course and Enrollment
from django.db.models import Q # For OR conditions in queries

register = template.Library()

@register.inclusion_tag('courses/partials/_recommended_courses_card.html', takes_context=True)
# UPDATED SIGNATURE AND PARAMETER NAMES:
# count: receives the '3'
# user_pedagogic_level_filter: receives 'user.pedagogic_level' (e.g., 'general')
# courses_to_exclude_from_list: receives 'displayed_course_ids' (e.g., [])
# current_course_id: Remains an optional keyword argument, useful for detail pages
def show_recommended_courses(context, count=3, user_pedagogic_level_filter=None, courses_to_exclude_from_list=None, current_course_id=None):
    """
    Returns a list of recommended, published courses based on user's pedagogic level.
    Excludes courses the user is already enrolled in, optionally a current course,
    and optionally a list of other course IDs (e.g., from a course listing page).
    """
    request = context['request']
    user = request.user
    recommended_courses_queryset = Course.objects.filter(is_published=True)

    # 1. Exclude courses the user is already enrolled in
    enrolled_course_ids = []
    if user.is_authenticated:
        enrolled_course_ids = Enrollment.objects.filter(student=user).values_list('course_id', flat=True)
        if enrolled_course_ids:
            recommended_courses_queryset = recommended_courses_queryset.exclude(id__in=list(enrolled_course_ids))

    # 2. Filter by User's Pedagogic Level (using the new `user_pedagogic_level_filter` parameter)
    # This parameter is passed from base.html (user.pedagogic_level)
    if user_pedagogic_level_filter:
        recommended_courses_queryset = recommended_courses_queryset.filter(
            Q(pedagogic_level=user_pedagogic_level_filter) | Q(pedagogic_level='general')
        )
    elif user.is_authenticated and user.pedagogic_level: # Fallback to actual user level if filter not provided
        recommended_courses_queryset = recommended_courses_queryset.filter(
            Q(pedagogic_level=user.pedagogic_level) | Q(pedagogic_level='general')
        )
    else:
        # For guest users or users without a level, only show 'general' courses
        recommended_courses_queryset = recommended_courses_queryset.filter(pedagogic_level='general')

    # 3. Exclude the current course (e.g., on a course detail page)
    # This parameter is expected to be passed as a keyword argument from a detail page
    if current_course_id:
        recommended_courses_queryset = recommended_courses_queryset.exclude(id=current_course_id)

    # 4. Exclude a list of specific course IDs (e.g., from the current course_list page)
    # This parameter receives `displayed_course_ids` from base.html
    if courses_to_exclude_from_list:
        # Ensure it's iterable; `displayed_course_ids` from the view should always be a list or tuple
        if isinstance(courses_to_exclude_from_list, (list, tuple)):
            recommended_courses_queryset = recommended_courses_queryset.exclude(id__in=courses_to_exclude_from_list)
        # Removed `elif isinstance(exclude_ids, int)` because `displayed_course_ids`
        # is always expected to be a list of IDs. If you pass a single ID, put it in a list [id].


    # Order randomly and limit the count for the initial grab
    recommended_courses = list(recommended_courses_queryset.order_by('?')[:count])

    # Fallback/Fill-up logic: If not enough specific courses, get more general ones
    if len(recommended_courses) < count:
        already_recommended_ids = [c.id for c in recommended_courses]
        all_excluded_ids = list(enrolled_course_ids) + already_recommended_ids
        if current_course_id:
            all_excluded_ids.append(current_course_id)
        if courses_to_exclude_from_list: # Use the new parameter name
            if isinstance(courses_to_exclude_from_list, (list, tuple)):
                all_excluded_ids.extend(courses_to_exclude_from_list)

        # Get general published courses, excluding anything already seen or recommended
        additional_courses_queryset = Course.objects.filter(is_published=True).exclude(id__in=list(set(all_excluded_ids)))

        additional_courses = list(additional_courses_queryset.order_by('?')[:count - len(recommended_courses)])
        recommended_courses.extend(additional_courses)

    return {'recommended_courses': recommended_courses}