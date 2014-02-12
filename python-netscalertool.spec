%define _topdir %(pwd)
%define _tmppath %{_topdir}
%define _builddir %{_tmppath}
%define _buildrootdir %{_tmppath}

%define _rpmtopdir %{_topdir}
%define _sourcedir %{_rpmtopdir}
%define _specdir %{_topdir}
%define _rpmdir %{_topdir}
%define _srcrpmdir %{_topdir}
%define _rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm

%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           TAGpython-netscalertool
Version:        %(%{__python} setup.py --version)
Release:        1%{?dist}
Summary:        Nitro API tool for managing NetScalers

Group:          Development/Tools
License:        MIT
URL:            http://www.tagged.com/
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

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/var/log/netscaler-tool/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{python_sitelib}/*
/usr/local/bin/netscaler-tool
%attr(0775,-,siteops) /var/log/netscaler-tool/

%changelog