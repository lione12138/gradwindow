"""Apply eight official course identity reviews completed on 2026-10-12."""

from review_ucl_ioe_renames import apply_reviewed_renames

from gradwindow.programme_adapters.ucl import REVIEWED_COURSE_IDENTITIES

SOURCES = {
    "Teaching of English to Speakers of Other Languages: Pre-Service MA": (
        "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/teaching-english-speakers-other-languages-tesol-pre-service-ma-2026; "
        "https://www.ucl.ac.uk/study/prospective-students/graduate/courses/teaching-english-speakers-other-languages-pre-service-ma"
    ),
    "Teaching of English to Speakers of Other Languages (In-Service) MA": (
        "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/teaching-english-speakers-other-languages-tesol-service-ma-2026; "
        "https://www.ucl.ac.uk/study/prospective-students/graduate/courses/teaching-english-speakers-other-languages-service-ma"
    ),
    "Civil Engineering (Integrated Design) MSc": (
        "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/civil-engineering-integrated-design-msc-2026; "
        "https://www.ucl.ac.uk/study/prospective-students/graduate/courses/civil-engineering-msc?option=TMSENG00123A"
    ),
    "Crime Science with Serious and Organised Crime MSc": (
        "https://www.ucl.ac.uk/study/prospective-students/graduate/courses/crime-science-msc?option=TMSENG00263A; "
        "https://www.ucl.ac.uk/engineering/security-crime-science/study/postgraduate-taught/crime-science-msc"
    ),
    "Translation and Technology (Interpreting) MSc": (
        "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/translation-and-technology-interpreting-msc-2026; "
        "https://www.ucl.ac.uk/study/prospective-students/graduate/courses/translation-and-technology-msc?option=TMSART00032A"
    ),
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
