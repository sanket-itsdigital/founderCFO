from django.shortcuts import redirect, render


# Create your views here.


def add_faq(request):

    if request.method == "POST":

        forms = faq_Form(request.POST, request.FILES)

        if forms.is_valid():
            forms.save()
            return redirect("list_faq")
        else:
            print(forms.errors)
            context = {"form": forms}
            return render(request, "add_faq.html", context)

    else:

        return render(request, "add_faq.html", {"form": faq_Form()})


def list_faq(request):

    data = FAQ.objects.all().order_by("-id")

    return render(request, "list_faq.html", {"data": data})


def update_faq(request, faq_id):

    instance = FAQ.objects.get(id=faq_id)

    if request.method == "POST":

        forms = faq_Form(request.POST, instance=instance)

        if forms.is_valid():
            forms.save()
            return redirect("list_faq")
        else:
            print(forms.errors)
            context = {"form": forms}
            return render(request, "add_faq.html", context)

    else:

        # create first row using admin then editing only

        forms = faq_Form(instance=instance)

        context = {"form": forms}

        return render(request, "add_faq.html", context)


def delete_faq(request, faq_id):

    data = FAQ.objects.get(id=faq_id).delete()

    return redirect("list_faq")
