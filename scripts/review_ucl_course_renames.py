"""Apply three official course identity reviews completed on 2026-10-12."""

from review_ucl_ioe_renames import apply_reviewed_renames

from gradwindow.programme_adapters.ucl import REVIEWED_COURSE_IDENTITIES

SOURCES = {
    "Energy Systems and Data Analytics MSc": (
        "https://www.ucl.ac.uk/bartlett/news/2022/mar/energy-systems-and-data-analytics-msc-students-come-second-energy-idea-challenge"
    ),
    "Public Health MPH": (
        "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/master-public-health-mph-2026; "
        "https://www.ucl.ac.uk/study/prospective-students/graduate/courses/public-health-mph"
    ),
    "Manufacturing with Innovation and Entrepreneurship MSc": (
        "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/manufacturing-innovation-and-enterprise-msc-2026; "
        "https://www.ucl.ac.uk/study/prospective-students/graduate/courses/manufacturing-innovation-and-entrepreneurship-msc"
    ),
}

if __name__ == "__main__":
    apply_reviewed_renames(REVIEWED_COURSE_IDENTITIES, SOURCES)
