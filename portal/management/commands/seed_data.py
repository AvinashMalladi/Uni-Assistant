import random

from django.core.management.base import BaseCommand

from portal.models import Department, Notice, SemesterResult


DEPARTMENTS = ['CSE', 'ECE', 'EEE', 'MECH', 'CIVIL']


class Command(BaseCommand):
    help = "Seed dummy departments, semester results, and notices for the demo portal."

    def handle(self, *args, **options):
        random.seed(42)  # reproducible demo numbers

        for code in DEPARTMENTS:
            Department.objects.get_or_create(code=code, defaults={'name': f"{code} Department"})

        created = 0
        for dept in DEPARTMENTS:
            for year in range(1, 5):
                for sem in (1, 2):
                    total = random.randint(55, 120)
                    pass_pct = round(random.uniform(62, 96), 1)
                    _, was_created = SemesterResult.objects.get_or_create(
                        department=dept, year=year, semester=sem,
                        defaults={'pass_percentage': pass_pct, 'total_students': total},
                    )
                    created += 1 if was_created else 0

        Notice.objects.get_or_create(
            title="Mid-Term Make-up Exam Registration Open",
            defaults={'body': "Register on SRAAP before the notified deadline. Late fee applies after."},
        )
        Notice.objects.get_or_create(
            title="Attendance Condonation Window",
            defaults={'body': "Students between 65-75% attendance can submit condonation requests this week."},
        )
        Notice.objects.get_or_create(
            title="Sparkrill 2027 - Save the Date",
            defaults={'body': "The annual cultural fest returns in the last week of January."},
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(DEPARTMENTS)} departments, {created} new semester results, and notices."
        ))
