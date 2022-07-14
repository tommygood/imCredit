from django import forms
from django.utils.translation import gettext_lazy as _
from .models import excelData, userLec
class CreditForm(forms.Form) :
    domain = forms.ChoiceField(
            required=True,
            widget=forms.RadioSelect(
                attrs={'class':'domain'}),
            choices=((1, "資訊技術與系統開發次領域"), (2, "資訊管理與決策科學次領域"))
    )
    year = forms.ChoiceField(
            required=True,
            widget=forms.RadioSelect(
                attrs={'class':'year'}),
            choices=((107, "107學年度"), (108, '108學年度'))
    )

class userForm(forms.ModelForm) :
    class Meta :
        model = userLec
        fields = ("all_data",)
        labels = {"all_data" : _("")}
        widgets = {'all_data' : forms.Textarea(attrs={'class':'text'})}
        #text = forms.CharField(
                #widget = forms.Textarea(attrs={'class':'text'})
                #)


class excelForm(forms.ModelForm) :
    class Meta :
        model = excelData
        fields = ("excel_data",)
        labels = {"excel_data" : _("excel資料")}
            #labels = {"excel_data" : _("excel資料"), "name" : _("帳號"), "password" : _("密碼")}
            #widgets = {'password': forms.PasswordInput(),}

class excelLogin(forms.Form) :
    name = forms.CharField(required=False)
    password = forms.CharField(required=False, widget = forms.PasswordInput())

