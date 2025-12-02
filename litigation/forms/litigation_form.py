
# from django import forms

# class faq_Form(forms.ModelForm):
#     class Meta:
#         model = FAQ
#         fields = ["question", "answer"]
#         widgets = {
#             "question": forms.Textarea(
#                 attrs={
#                     "cols": 40,
#                     "rows": 5,
#                     "class": "form-control description-box",
#                     "placeholder": "Enter your question here...",
#                 }
#             ),
#             "answer": forms.Textarea(
#                 attrs={
#                     "cols": 40,
#                     "rows": 7,
#                     "class": "form-control description-box",
#                     "placeholder": "Enter the answer...",
#                 }
#             ),
#         }