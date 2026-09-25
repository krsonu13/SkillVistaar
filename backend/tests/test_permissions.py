from app.core.permissions import (
    ASSESSMENT_MANAGER,
    APPROVE_VERIFICATION,
    ANALYZE_GOVERNMENT_DATA,
    CANDIDATE,
    CREATE_ASSESSMENT,
    CREATE_COURSE,
    CREATE_JOB,
    GOVERNMENT_ADMIN,
    GOVERNMENT_VERIFIER,
    HR,
    INSTITUTION_ADMIN,
    MANAGE_GOVERNMENT_DATA_ACCESS,
    MANAGE_ORGANIZATION,
    MANAGE_ORGANIZATION_MEMBERS,
    ORG_ADMIN,
    REVIEW_VERIFICATION,
    SUPER_ADMIN,
    TAKE_ASSESSMENT,
    UPDATE_JOB,
    VIEW_AUDIT_LOGS,
    VIEW_GOVERNMENT_ANALYTICS,
    VIEW_JOBS,
    VIEW_LABOUR_MARKET,
    VIEW_OWN_PROFILE,
    VIEW_CREDENTIALS,
    VIEW_COURSES,
    VIEW_SKILLS,
    get_permissions_for_roles,
    has_any_role,
    has_permission,
    has_role,
)


def test_candidate_permissions():
    roles = [CANDIDATE]
    permissions = get_permissions_for_roles(roles)

    assert VIEW_OWN_PROFILE in permissions
    assert VIEW_JOBS in permissions
    assert VIEW_SKILLS in permissions
    assert VIEW_CREDENTIALS in permissions
    assert VIEW_COURSES in permissions
    assert TAKE_ASSESSMENT in permissions

    assert CREATE_JOB not in permissions
    assert APPROVE_VERIFICATION not in permissions
    assert VIEW_AUDIT_LOGS not in permissions


def test_employer_org_admin_permissions():
    roles = [ORG_ADMIN]
    permissions = get_permissions_for_roles(roles)

    assert VIEW_OWN_PROFILE in permissions
    assert VIEW_JOBS in permissions
    assert CREATE_JOB in permissions
    assert UPDATE_JOB in permissions
    assert MANAGE_ORGANIZATION in permissions
    assert MANAGE_ORGANIZATION_MEMBERS in permissions
    assert CREATE_ASSESSMENT in permissions

    assert APPROVE_VERIFICATION not in permissions
    assert MANAGE_GOVERNMENT_DATA_ACCESS not in permissions


def test_employer_hr_permissions():
    roles = [HR]
    permissions = get_permissions_for_roles(roles)

    assert VIEW_JOBS in permissions
    assert CREATE_JOB in permissions
    assert UPDATE_JOB in permissions
    assert CREATE_ASSESSMENT in permissions

    assert MANAGE_ORGANIZATION not in permissions
    assert MANAGE_ORGANIZATION_MEMBERS not in permissions
    assert APPROVE_VERIFICATION not in permissions


def test_government_verifier_permissions():
    roles = [GOVERNMENT_VERIFIER]
    permissions = get_permissions_for_roles(roles)

    assert REVIEW_VERIFICATION in permissions
    assert APPROVE_VERIFICATION in permissions
    assert VIEW_GOVERNMENT_ANALYTICS in permissions
    assert VIEW_LABOUR_MARKET in permissions
    assert VIEW_CREDENTIALS in permissions

    assert CREATE_JOB not in permissions
    assert CREATE_COURSE not in permissions
    assert MANAGE_GOVERNMENT_DATA_ACCESS not in permissions


def test_government_admin_permissions():
    roles = [GOVERNMENT_ADMIN]
    permissions = get_permissions_for_roles(roles)

    assert REVIEW_VERIFICATION in permissions
    assert APPROVE_VERIFICATION in permissions
    assert VIEW_GOVERNMENT_ANALYTICS in permissions
    assert ANALYZE_GOVERNMENT_DATA in permissions
    assert VIEW_LABOUR_MARKET in permissions

    assert MANAGE_GOVERNMENT_DATA_ACCESS not in permissions
    assert VIEW_AUDIT_LOGS in permissions


def test_institution_admin_permissions():
    roles = [INSTITUTION_ADMIN]
    permissions = get_permissions_for_roles(roles)

    assert VIEW_COURSES in permissions
    assert CREATE_COURSE in permissions
    assert VIEW_SKILLS in permissions
    assert VIEW_CREDENTIALS in permissions
    assert VIEW_LABOUR_MARKET in permissions

    assert CREATE_JOB not in permissions
    assert APPROVE_VERIFICATION not in permissions


def test_super_admin_has_administrative_permissions():
    roles = [SUPER_ADMIN]
    permissions = get_permissions_for_roles(roles)

    assert APPROVE_VERIFICATION in permissions
    assert MANAGE_GOVERNMENT_DATA_ACCESS in permissions
    assert VIEW_AUDIT_LOGS in permissions
    assert CREATE_JOB in permissions
    assert CREATE_COURSE in permissions
    assert CREATE_ASSESSMENT in permissions
    assert VIEW_GOVERNMENT_ANALYTICS in permissions


def test_multiple_roles_combine_permissions():
    roles = [HR, ASSESSMENT_MANAGER]

    permissions = get_permissions_for_roles(roles)

    assert CREATE_JOB in permissions
    assert CREATE_ASSESSMENT in permissions
    assert VIEW_JOBS in permissions


def test_has_role():
    roles = [CANDIDATE, HR]

    assert has_role(roles, CANDIDATE)
    assert has_role(roles, HR)

    assert not has_role(
        roles,
        SUPER_ADMIN,
    )


def test_has_any_role():
    roles = [CANDIDATE]

    assert has_any_role(
        roles,
        [CANDIDATE, HR],
    )

    assert not has_any_role(
        roles,
        [HR, ORG_ADMIN],
    )


def test_has_permission():
    roles = [ORG_ADMIN]

    assert has_permission(
        roles,
        CREATE_JOB,
    )

    assert not has_permission(
        roles,
        APPROVE_VERIFICATION,
    )


def test_unknown_role_has_no_permissions():
    roles = ["UNKNOWN_ROLE"]

    permissions = get_permissions_for_roles(roles)

    assert permissions == set()

    assert not has_permission(
        roles,
        CREATE_JOB,
    )