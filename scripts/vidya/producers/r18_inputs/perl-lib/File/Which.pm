package File::Which;
use strict;
use warnings;
use Exporter 'import';
our @EXPORT = qw(which);
sub which {
    my ($name) = @_;
    return undef unless defined $name && length $name;
    for my $dir (split /:/, $ENV{PATH} // '') {
        my $p = "$dir/$name";
        return $p if -f $p && -x $p;
    }
    return undef;
}
1;
