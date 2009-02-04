require File.dirname(__FILE__) + "/../test_helper.rb"

module Hello
  def hello
    "Hello"
  end
end

describe "Scoping" do
  include Hello
  it "has access to included module" do
    hello.should == "Hello"
  end
  
  describe "in nested context" do
    it "has access to included module" do
      hello.should == "Hello"
    end
  end
end


