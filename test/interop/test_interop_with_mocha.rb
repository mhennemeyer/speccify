require File.dirname(__FILE__) + "/../test_helper.rb"
require 'rubygems'
require 'mocha'

describe "Testing with mocha" do
  it "verifies expectations" do
    @var = Object.new
    @var.expects(:hello)
    @var.hello
  end
end