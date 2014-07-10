%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-netscaler-tool
Version:        1.25.1
Release:        1%{?dist}
Summary:        Managed Citrix NetScaler using Nitro API
Source0:        netscaler-tool-%{version}.tar.gz

Group:          Development/Tools
License:        Apache v2.0
URL:            http://www.github.com/tagged/netscaler-tool
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel
Requires:       python-argparse
Requires:       python-httplib2
Requires:       python-setuptools

%description
Managed Citrix NetScaler using Nitro API

%prep
%setup -q -n netscaler-tool-%{version}

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
install -D netscalertool.conf.example $RPM_BUILD_ROOT/etc/netscalertool.conf
mkdir -p $RPM_BUILD_ROOT/var/log/netscaler-tool/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{python_sitelib}/*
%config /etc/netscalertool.conf
/usr/bin/netscaler-tool
/var/log/netscaler-tool

%changelog
