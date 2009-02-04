require File.dirname(__FILE__) + "/rails_test_helper.rb"
require 'performance_test_help'

describe "Browsing", :type => ActionController::PerformanceTest do
  it "get homepage" do
    get '/'
  end
end