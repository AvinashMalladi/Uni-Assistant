from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class SemesterResult(models.Model):
    """Dummy pre-seeded pass-percentage data the chatbot's RAG/tool layer can
    query once slots (year, semester, department) are filled. In a real
    deployment this would come from the SRAAP academic database."""
    department = models.CharField(max_length=10)  # e.g. CSE, ECE, EEE, MECH, CIVIL
    year = models.PositiveSmallIntegerField()      # 1-4
    semester = models.PositiveSmallIntegerField()  # 1 or 2 (odd/even)
    pass_percentage = models.FloatField()
    total_students = models.PositiveIntegerField()

    class Meta:
        unique_together = ('department', 'year', 'semester')

    def __str__(self):
        return f"{self.department} Y{self.year} S{self.semester}: {self.pass_percentage}%"


class Notice(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    posted_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title
