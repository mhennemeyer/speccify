require 'rubygems'
require 'tempfile'
require File.dirname(__FILE__) + "/../../lib/midi_spec.rb"

def_matcher :match do |given, matcher, args|
  given.index(args[0]) != nil
end

def_matcher :be_blank do |given, matcher, args|
  given == nil #|| given.blank? == true
end

def ruby(args, stderr=nil)
  config       = ::Config::CONFIG
  interpreter  = File::join(config['bindir'], config['ruby_install_name']) + config['EXEEXT']
  cmd = "#{interpreter} #{args}"
  cmd << " 2> #{stderr}" unless stderr.nil?
  `#{cmd}`
end

def ruby19(args, stderr=nil)
  cmd = "ruby1.9 #{args}"
  cmd << " 2> #{stderr}" unless stderr.nil?
  `#{cmd}`
end
