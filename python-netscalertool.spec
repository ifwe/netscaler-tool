%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-netscaler-tool
Version:        1.17
Release:        1%{?dist}
Summary:        Nitro API tool for managing NetScalers
Source0:        netscaler-tool-%{version}.tgz

Group:          Development/Tools
License:        Apache v2.0
URL:            http://www.github.com/tagged/netscaler-tool
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel
Requires:       python-argparse
Requires:       python-httplib2
Requires:       python-setuptools
%if 0%{?rhel} <= 5
Requires:       python-simplejson
%endif

%description
Nitro API tool for managing NetScalers

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{python_sitelib}/*
/usr/bin/netscaler-tool

%changelog
